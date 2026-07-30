"""
WebSocket — 交互式 SSH 终端
浏览器中打开 SSH 终端 → WebSocket → 后端 asyncssh → 板子
"""
import asyncio, json
import asyncssh
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.db.database import get_db
from app.models.board import Board, ConnType
from app.models.user import User
from app.models.booking import Booking
from app.config import settings

router = APIRouter(tags=["WS-SSH终端"])


@router.websocket("/ws/ssh-terminal/{board_id}")
async def ssh_terminal(
    ws: WebSocket,
    board_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    # 认证
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, ValueError):
        await ws.close(code=4001, reason="无效令牌")
        return

    user = await db.get(User, user_id)
    if not user:
        await ws.close(code=4001, reason="用户不存在")
        return

    board = await db.get(Board, board_id)
    if not board or board.conn_type != ConnType.SSH.value:
        await ws.close(code=4002, reason="板子不存在或不是SSH类型")
        return

    # 预约门控 (admin 跳过)
    if user.role != "admin":
        from sqlalchemy import select as sa_select, and_
        result = await db.execute(
            sa_select(Booking).where(
                and_(Booking.user_id == user.id, Booking.board_id == board_id,
                     Booking.status == "active")
            )
        )
        if not result.scalar_one_or_none():
            await ws.close(code=4003, reason="需要先预约该板子")
            return

    await ws.accept()

    ssh_conn = None
    ssh_session = None

    try:
        # 建立 SSH 连接
        kwargs = {
            "host": board.host,
            "port": board.port or 22,
            "username": board.username or "root",
            "known_hosts": None,
            "connect_timeout": 15,
        }
        if board.ssh_password:
            kwargs["password"] = board.ssh_password

        ssh_conn = await asyncssh.connect(**kwargs)

        # 创建交互式 PTY shell
        class ShellSession(asyncssh.SSHClientSession):
            def __init__(self):
                self._chan = None
            def connection_made(self, chan):
                self._chan = chan
            def shell_requested(self):
                return True
            def session_started(self):
                pass
            def data_received(self, data, datatype):
                ws_passthrough_queue.put_nowait(("data", data))
            def connection_lost(self, exc):
                ws_passthrough_queue.put_nowait(("closed", str(exc) if exc else ""))

        ws_passthrough_queue = asyncio.Queue()

        ssh_session, _ = await ssh_conn.create_session(
            lambda: ShellSession(),
            term_type="xterm-256color",
            term_size=(80, 24),
        )

        await ws.send_text(json.dumps({
            "type": "connected",
            "host": board.host,
            "board_name": board.name,
            "message": f"SSH {board.username}@{board.host}:{board.port or 22}",
        }))

        # 双向桥接
        async def ssh_to_ws():
            while True:
                typ, payload = await ws_passthrough_queue.get()
                if typ == "closed":
                    try: await ws.close()
                    except: pass
                    break
                elif typ == "data":
                    await ws.send_text(json.dumps({
                        "type": "data",
                        "text": payload.decode("utf-8", errors="replace"),
                    }))

        async def ws_to_ssh():
            while True:
                try:
                    raw = await ws.receive_text()
                except WebSocketDisconnect:
                    break
                try:
                    msg = json.loads(raw)
                    if msg.get("type") == "input":
                        ssh_session.stdin.write(msg["text"].encode())
                except json.JSONDecodeError:
                    ssh_session.stdin.write(raw.encode())

        read_task = asyncio.create_task(ssh_to_ws())
        write_task = asyncio.create_task(ws_to_ssh())

        # 等两个任务之一结束
        done, pending = await asyncio.wait(
            [read_task, write_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

    except asyncssh.Error as e:
        try:
            await ws.send_text(json.dumps({
                "type": "error",
                "text": f"SSH连接失败: {e}",
            }))
        except Exception:
            pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({
                "type": "error",
                "text": f"终端错误: {e}",
            }))
        except Exception:
            pass
    finally:
        if ssh_session:
            ssh_session.close()
        if ssh_conn:
            ssh_conn.close()
