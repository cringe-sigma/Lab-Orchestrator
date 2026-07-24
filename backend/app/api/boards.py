"""板子管理 API"""
from __future__ import annotations

import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.board import Board, BoardStatus, BoardType, ConnType
from app.models.user import User
from app.api.auth import get_current_user
from app.services.board_manager import board_manager
from app.api.ws_boards import get_remote_ws, send_to_remote

router = APIRouter(prefix="/api/boards", tags=["板子管理"])


class BoardCreate(BaseModel):
    name: str
    board_type: str = "linux"
    conn_type: str = "ssh"
    host: str = ""
    port: int = 22
    username: str = ""
    serial_port: str = ""
    serial_baud: int = 115200
    tags: str = ""
    description: str = ""


class BoardResponse(BaseModel):
    id: int
    name: str
    board_type: str
    status: str
    conn_type: str
    host: str
    port: int
    serial_port: str
    board_token: str | None = None  # 仅 remote 类型显示
    tags: str
    description: str
    locked_by: int | None
    is_active: bool
    last_heartbeat: str | None


class BoardConnect(BaseModel):
    password: str = ""


@router.get("/", response_model=list[BoardResponse])
async def list_boards(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取所有板子"""
    result = await db.execute(select(Board).where(Board.is_active == True))
    boards = result.scalars().all()
    return [_board_to_response(b) for b in boards]


def _board_to_response(b: Board) -> BoardResponse:
    return BoardResponse(
        id=b.id, name=b.name, board_type=b.board_type, status=b.status,
        conn_type=b.conn_type, host=b.host or "", port=b.port or 22,
        serial_port=b.serial_port or "",
        board_token=b.board_token if b.conn_type == ConnType.REMOTE.value else None,
        tags=b.tags or "", description=b.description or "",
        locked_by=b.locked_by, is_active=b.is_active,
        last_heartbeat=b.last_heartbeat.isoformat() if b.last_heartbeat else None,
    )


@router.post("/", response_model=BoardResponse)
async def create_board(data: BoardCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """添加新板子（remote 类型自动生成 board_token）"""
    board_token = None
    if data.conn_type == ConnType.REMOTE.value:
        board_token = secrets.token_urlsafe(24)

    board = Board(
        name=data.name, board_type=data.board_type,
        conn_type=data.conn_type, host=data.host, port=data.port,
        username=data.username, serial_port=data.serial_port,
        serial_baud=data.serial_baud, tags=data.tags, description=data.description,
        board_token=board_token,
    )
    db.add(board)
    await db.commit()
    await db.refresh(board)
    return _board_to_response(board)


@router.get("/{board_id}", response_model=BoardResponse)
async def get_board(board_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取单块板子信息"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")
    return _board_to_response(board)


@router.post("/{board_id}/check")
async def check_board(board_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """检查板子连通性"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")

    # 远程板子: 检查 WebSocket 是否在线
    if board.conn_type == ConnType.REMOTE.value:
        ws_connected = get_remote_ws(board_id) is not None
        board.status = BoardStatus.ONLINE.value if ws_connected else BoardStatus.OFFLINE.value
    else:
        status = await board_manager.check_health(board)
        board.status = status.value

    board.last_heartbeat = datetime.utcnow()
    await db.commit()
    return {"board_id": board_id, "status": board.status}


@router.post("/{board_id}/exec")
async def exec_on_board(
    board_id: int, data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """在板子上执行命令（本地SSH/串口 或 远程WebSocket）"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")
    if board.locked_by and board.locked_by != user.id:
        raise HTTPException(status_code=403, detail="板子已被其他用户占用")

    command = data.get("command", "")
    password = data.get("password", "")

    # 远程板子: 通过 WebSocket 下发命令
    if board.conn_type == ConnType.REMOTE.value:
        result = await send_to_remote(board_id, command)
        return result

    # 本地板子: 通过 SSH/串口 执行
    output = await board_manager.exec_on_board(board, command, password)
    return {"output": output}
