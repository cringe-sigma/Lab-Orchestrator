"""WebSocket 中继 — bridge.ps1 ↔ xterm.js"""
import asyncio, json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WS-Bridge终端"])

# board_id → bridge WebSocket
_bridge_sockets: dict[int, WebSocket] = {}
# board_id → client WebSocket
_client_sockets: dict[int, WebSocket] = {}


@router.websocket("/ws/bridge-terminal/{board_id}")
async def bridge_terminal(ws: WebSocket, board_id: int):
    """bridge.ps1 或 前端xterm.js 连接此端点，服务器中继双方"""

    # 通过消息头区分bridge还是client
    # bridge发送register消息，client不发送
    await ws.accept()

    is_bridge = False
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=5)
        msg = json.loads(raw)
        if msg.get("type") == "register":
            is_bridge = True
    except asyncio.TimeoutError:
        is_bridge = False  # client (xterm.js doesn't send register)

    if is_bridge:
        _bridge_sockets[board_id] = ws
        try:
            while True:
                data = await ws.receive_text()
                client = _client_sockets.get(board_id)
                if client:
                    await client.send_text(data)
        except WebSocketDisconnect:
            pass
        finally:
            _bridge_sockets.pop(board_id, None)
    else:
        _client_sockets[board_id] = ws
        try:
            while True:
                data = await ws.receive_text()
                bridge = _bridge_sockets.get(board_id)
                if bridge:
                    await bridge.send_text(data)
        except WebSocketDisconnect:
            pass
        finally:
            _client_sockets.pop(board_id, None)
