"""板子管理 API"""
from __future__ import annotations

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
    return [
        BoardResponse(
            id=b.id, name=b.name, board_type=b.board_type, status=b.status,
            conn_type=b.conn_type, host=b.host or "", port=b.port or 22,
            serial_port=b.serial_port or "", tags=b.tags or "",
            description=b.description or "", locked_by=b.locked_by,
            is_active=b.is_active,
            last_heartbeat=b.last_heartbeat.isoformat() if b.last_heartbeat else None,
        )
        for b in boards
    ]


@router.post("/", response_model=BoardResponse)
async def create_board(data: BoardCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """添加新板子"""
    board = Board(
        name=data.name, board_type=data.board_type,
        conn_type=data.conn_type, host=data.host, port=data.port,
        username=data.username, serial_port=data.serial_port,
        serial_baud=data.serial_baud, tags=data.tags, description=data.description,
    )
    db.add(board)
    await db.commit()
    await db.refresh(board)
    return BoardResponse(
        id=board.id, name=board.name, board_type=board.board_type, status=board.status,
        conn_type=board.conn_type, host=board.host or "", port=board.port or 22,
        serial_port=board.serial_port or "", tags=board.tags or "",
        description=board.description or "", locked_by=board.locked_by,
        is_active=board.is_active,
        last_heartbeat=board.last_heartbeat.isoformat() if board.last_heartbeat else None,
    )


@router.get("/{board_id}", response_model=BoardResponse)
async def get_board(board_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取单块板子信息"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")
    return BoardResponse(
        id=board.id, name=board.name, board_type=board.board_type, status=board.status,
        conn_type=board.conn_type, host=board.host or "", port=board.port or 22,
        serial_port=board.serial_port or "", tags=board.tags or "",
        description=board.description or "", locked_by=board.locked_by,
        is_active=board.is_active,
        last_heartbeat=board.last_heartbeat.isoformat() if board.last_heartbeat else None,
    )


@router.post("/{board_id}/check")
async def check_board(board_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """检查板子连通性"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")
    status = await board_manager.check_health(board)
    board.status = status.value
    board.last_heartbeat = datetime.utcnow()
    await db.commit()
    return {"board_id": board_id, "status": status.value}


@router.post("/{board_id}/exec")
async def exec_on_board(
    board_id: int, data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """在板子上执行命令"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")
    if board.locked_by and board.locked_by != user.id:
        raise HTTPException(status_code=403, detail="板子已被其他用户占用")

    command = data.get("command", "")
    password = data.get("password", "")
    output = await board_manager.exec_on_board(board, command, password)
    return {"output": output}
