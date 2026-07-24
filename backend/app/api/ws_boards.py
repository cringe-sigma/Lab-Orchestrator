"""
WebSocket — 远程板子 Agent 连接端点

远程板子通过 WebSocket 主动连接服务器:
  板子 Agent ──ws://server:8000/ws/board?token=XXX──→ 服务器

连接后:
  服务器 ←→ 板子: 双向消息
    服务器 → 板子: execute(执行命令) / heartbeat / shutdown
    板子 → 服务器: register(注册) / result(返回结果) / heartbeat_ack
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.board import Board, BoardStatus, ConnType

router = APIRouter(tags=["WS-板子代理"])

# 在线远程板子 {board_id: WebSocket}
_remote_connections: dict[int, WebSocket] = {}


def get_remote_ws(board_id: int) -> WebSocket | None:
    """获取远程板子的 WebSocket 连接"""
    return _remote_connections.get(board_id)


# ===== WebSocket 端点 =====

@router.websocket("/ws/board")
async def board_agent_ws(
    ws: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """远程板子 Agent 连接端点"""
    await ws.accept()
    board_id = None

    try:
        # 1. 等待注册消息
        raw = await ws.receive_text()
        msg = json.loads(raw)

        if msg.get("type") != "register":
            await ws.send_json({"type": "error", "detail": "需要先发送注册消息"})
            return

        # 2. 验证 token，绑定板子
        board = await _auth_board(token, db)
        if not board:
            await ws.send_json({"type": "error", "detail": "无效的 board_token"})
            return

        board_id = board.id
        board.status = BoardStatus.ONLINE.value
        board.last_heartbeat = datetime.utcnow()
        await db.commit()

        _remote_connections[board_id] = ws
        print(f"[WS] 板子注册成功: {board.name} (id={board_id})")

        # 确认注册
        await ws.send_json({
            "type": "registered",
            "board_id": board_id,
            "board_name": board.name,
        })

        # 3. 消息循环 — 接收板子的执行结果
        while True:
            try:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "heartbeat_ack":
                    board.last_heartbeat = datetime.utcnow()
                    board.status = BoardStatus.ONLINE.value
                    await db.commit()

                elif msg_type == "result":
                    # 结果会有回调处理，记录日志即可
                    await _store_result(msg, board_id, db)

            except json.JSONDecodeError:
                continue

    except WebSocketDisconnect:
        print(f"[WS] 板子断开: board_id={board_id}")

    finally:
        if board_id:
            _remote_connections.pop(board_id, None)
            # 更新状态为离线
            try:
                board = await db.get(Board, board_id)
                if board:
                    board.status = BoardStatus.OFFLINE.value
                    await db.commit()
            except Exception:
                pass


async def _auth_board(token: str, db: AsyncSession) -> Board | None:
    """验证 board_token"""
    result = await db.execute(
        select(Board).where(
            Board.board_token == token,
            Board.conn_type == ConnType.REMOTE.value,
            Board.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def _store_result(msg: dict, board_id: int, db: AsyncSession):
    """存储执行结果到数据库(可扩展为日志表)"""
    # 当前仅打印，后续可存入 experiment log
    cmd_id = msg.get("cmd_id", "?")
    output = msg.get("output", "")[:200]
    print(f"[WS] board={board_id} cmd={cmd_id} result={output}...")


# ===== 向远程板子下发命令 =====

async def send_to_remote(board_id: int, command: str, timeout: int = 60) -> dict:
    """向远程板子发送命令并等待结果"""
    ws = _remote_connections.get(board_id)
    if not ws:
        return {"error": "板子未在线(WebSocket 未连接)"}

    cmd_id = str(uuid.uuid4())[:8]
    try:
        await ws.send_json({
            "type": "execute",
            "cmd_id": cmd_id,
            "command": command,
            "timeout": timeout,
        })

        # 等待返回结果(简单重试超时机制)
        import asyncio
        for _ in range(timeout * 2):  # 每0.5s检查一次
            await asyncio.sleep(0.5)
            # 结果由消息循环接收，这里简化处理
            # 实际生产建议用 asyncio.Event 或回调队列

        return {"output": "命令已发送到远程板子, 等待结果回调", "cmd_id": cmd_id}

    except Exception as e:
        return {"error": str(e)}
