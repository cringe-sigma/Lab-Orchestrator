"""
WebSocket — 交互式串口终端

用户在浏览器中打开串口终端 → WebSocket → 后端打开串口 → 双向通信

流程:
  用户输入 → WS → 后端写串口 → 板子
  板子输出 → 串口读取 → WS → 前端终端显示
"""
from __future__ import annotations

import asyncio
import json
import serial  # pyserial
import serial.tools.list_ports
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.board import Board, ConnType
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter(tags=["WS-串口终端"])

# 活跃的串口终端连接 {board_id: {ws, serial, task, ...}}
_active_terminals: dict[int, dict] = {}


@router.websocket("/ws/terminal/{board_id}")
async def serial_terminal(
    ws: WebSocket,
    board_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """交互式串口终端 WebSocket 端点"""

    # 认证
    from jose import jwt, JWTError
    from app.config import settings

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, ValueError):
        await ws.close(code=4001, reason="无效的认证令牌")
        return

    user = await db.get(User, user_id)
    if not user:
        await ws.close(code=4001, reason="用户不存在")
        return

    # 获取板子信息
    board = await db.get(Board, board_id)
    if not board or board.conn_type != ConnType.SERIAL.value:
        await ws.close(code=4002, reason="板子不存在或不是串口类型")
        return

    await ws.accept()

    ser = None
    read_task = None
    terminal_id = f"term_{board_id}"

    try:
        # 1. 打开串口
        port = board.serial_port or "COM1"
        baud = board.serial_baud or 115200

        ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05,  # 非阻塞读取
        )

        await ws.send_text(json.dumps({
            "type": "connected",
            "port": port,
            "baud": baud,
            "board_name": board.name,
            "message": f"串口 {port} @ {baud}bps 已连接",
        }))

        # 2. 存储连接信息
        _active_terminals[board_id] = {"ws": ws, "serial": ser, "task": None}

        # 3. 启动串口读取任务 (持续读串口 → 转发到前端)
        async def read_serial_loop():
            """持续从串口读取数据并发送到前端"""
            buffer = b""
            try:
                while True:
                    if ser and ser.is_open:
                        data = ser.read(1024)  # 每次读最多1024字节
                        if data:
                            # 尝试解码，失败则用 hex
                            try:
                                text = data.decode("utf-8", errors="replace")
                                await ws.send_text(json.dumps({
                                    "type": "data",
                                    "text": text,
                                }))
                            except Exception:
                                await ws.send_text(json.dumps({
                                    "type": "data",
                                    "hex": data.hex(),
                                }))
                    await asyncio.sleep(0.02)  # 50Hz 读取频率
            except asyncio.CancelledError:
                pass
            except Exception as e:
                try:
                    await ws.send_text(json.dumps({"type": "error", "text": f"读取错误: {e}"}))
                except Exception:
                    pass

        read_task = asyncio.create_task(read_serial_loop())
        _active_terminals[board_id]["task"] = read_task

        # 4. 主循环 — 接收用户输入 → 写串口
        while True:
            try:
                raw = await ws.receive_text()
                msg = json.loads(raw)

                msg_type = msg.get("type", "")

                if msg_type == "input":
                    # 用户输入 → 写串口
                    text = msg.get("text", "")
                    if ser and ser.is_open:
                        if msg.get("mode") == "hex":
                            ser.write(bytes.fromhex(text.replace(" ", "")))
                        else:
                            ser.write(text.encode("utf-8"))

                elif msg_type == "ctrl":
                    # 控制信号 (DTR/RTS)
                    signal = msg.get("signal", "")
                    if signal == "dtr" and ser:
                        ser.dtr = not ser.dtr
                    elif signal == "rts" and ser:
                        ser.rts = not ser.rts

                elif msg_type == "baud":
                    # 动态修改波特率
                    new_baud = msg.get("value", 115200)
                    if ser and ser.is_open:
                        ser.baudrate = new_baud
                        await ws.send_text(json.dumps({
                            "type": "info",
                            "text": f"波特率已改为 {new_baud}",
                        }))

                elif msg_type == "flush":
                    # 清空串口缓冲区
                    if ser and ser.is_open:
                        ser.reset_input_buffer()
                        ser.reset_output_buffer()
                        await ws.send_text(json.dumps({
                            "type": "info",
                            "text": "缓冲区已清空",
                        }))

            except json.JSONDecodeError:
                # 纯文本 → 直接写串口
                if ser and ser.is_open:
                    ser.write(raw.encode("utf-8"))

    except WebSocketDisconnect:
        pass

    except serial.SerialException as e:
        try:
            await ws.send_text(json.dumps({
                "type": "error",
                "text": f"串口错误: {e}",
            }))
        except Exception:
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
        # 5. 清理
        if read_task:
            read_task.cancel()
            try:
                await read_task
            except asyncio.CancelledError:
                pass

        if ser and ser.is_open:
            ser.close()

        _active_terminals.pop(board_id, None)
        print(f"[Terminal] 串口终端已关闭: board_id={board_id}")


@router.get("/api/terminal/ports")
async def list_serial_ports(user: User = Depends(get_current_user)):
    """列出服务器上的所有可用串口"""
    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append({
            "device": p.device,
            "name": p.name,
            "description": p.description,
            "hwid": p.hwid,
        })
    return {"ports": ports}
