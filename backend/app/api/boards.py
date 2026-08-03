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
from app.api.auth import get_current_user, verify_password
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
    ssh_password: str = ""
    # 跳板
    jump_host: str = ""
    jump_port: int = 22
    jump_username: str = ""
    jump_password: str = ""
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
        username=data.username, ssh_password=data.ssh_password or None,
        jump_host=data.jump_host or None, jump_port=data.jump_port or 22,
        jump_username=data.jump_username or None,
        jump_password=data.jump_password or None,
        serial_port=data.serial_port,
        serial_baud=data.serial_baud, tags=data.tags, description=data.description,
        board_token=board_token,
    )
    db.add(board)
    await db.commit()
    await db.refresh(board)

    # 审计日志
    await audit_log(db, user, "create", board_id=board.id, board_name=board.name)

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
        status = await board_manager.check_health(board, board.ssh_password or "")
        board.status = status.value

    board.last_heartbeat = datetime.utcnow()
    await db.commit()
    return {"board_id": board_id, "status": board.status}


# ================================================================
#  预约门控
# ================================================================

async def require_active_booking(
    board_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检查当前用户是否有该板子的活跃预约 (含共享, admin 跳过)"""
    from app.models.booking import Booking
    from sqlalchemy import and_, or_
    import json as _json

    if user.role == "admin":
        return True

    # 检查自己的预约
    result = await db.execute(
        select(Booking).where(
            and_(
                Booking.user_id == user.id,
                Booking.board_id == board_id,
                Booking.status == "active",
            )
        )
    )
    if result.scalar_one_or_none():
        return True

    # 检查共享预约
    all_active = await db.execute(
        select(Booking).where(
            and_(
                Booking.board_id == board_id,
                Booking.status == "active",
            )
        )
    )
    for bk in all_active.scalars().all():
        try:
            shared = _json.loads(bk.shared_with or "[]")
            if user.id in shared:
                return True
        except: pass

    raise HTTPException(
        status_code=403,
        detail="需要先预约该板子才能操作。请先创建预约并等待预约开始。",
    )
    return True


@router.post("/{board_id}/exec")
async def exec_on_board(
    board_id: int, data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    _booking_ok: bool = Depends(require_active_booking),
):
    """在板子上执行命令（需活跃预约，admin除外）"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")
    if board.locked_by and board.locked_by != user.id:
        raise HTTPException(status_code=403, detail="板子已被其他用户占用")

    command = data.get("command", "")
    password = data.get("password", "") or board.ssh_password or ""

    # 远程板子: 通过 HTTP 轮询队列下发命令
    if board.conn_type == ConnType.REMOTE.value:
        import uuid
        cmd_id = str(uuid.uuid4())[:8]
        _pending_commands.setdefault(board_id, []).append({
            "id": cmd_id, "command": command
        })
        # 等待结果 (最多 30 秒)
        import asyncio
        for _ in range(60):  # 30s max
            await asyncio.sleep(0.5)
            if cmd_id in _command_results:
                result = _command_results.pop(cmd_id)
                return {"output": result.get("output", "")}
        return {"output": "命令超时 (30s)"}

    # 本地板子: 通过 SSH/串口 执行
    output = await board_manager.exec_on_board(board, command, password)
    return {"output": output}


# ================================================================
#  板子删除 (需二次确认)
# ================================================================

class DeleteConfirm(BaseModel):
    password: str  # 输入当前账号密码来确认删除


async def audit_log(
    db: AsyncSession, user: User, action: str,
    board_id: int = None, board_name: str = "", details: str = ""
):
    """写入审计日志"""
    from app.models.audit_log import BoardAuditLog
    log = BoardAuditLog(
        user_id=user.id,
        username=user.username,
        action=action,
        board_id=board_id,
        board_name=board_name,
        details=details,
    )
    db.add(log)
    await db.commit()


@router.delete("/{board_id}")
async def delete_board(
    board_id: int,
    data: DeleteConfirm,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除板子 — 需输入当前账号密码二次确认"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以删除板子")

    # 密码验证
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=403, detail="密码错误")

    board_name = board.name
    board.is_active = False
    await db.commit()

    # 审计日志
    await audit_log(db, user, "delete", board_id=board_id, board_name=board_name)

    return {"success": True, "message": f"板子 '{board_name}' 已删除"}


# ================================================================
#  HTTP Agent 轮询模式 (替代 WebSocket)
# ================================================================
_pending_commands: dict[int, list[dict]] = {}  # board_id → [{id, command}]
_command_results: dict[str, dict] = {}         # cmd_id → {output, error}


@router.post("/register-agent")
async def register_http_agent(data: dict, db: AsyncSession = Depends(get_db)):
    """HTTP Agent 注册 — 通过 board_token 认证"""
    token = data.get("token", "")
    result = await db.execute(
        select(Board).where(
            Board.board_token == token,
            Board.conn_type == ConnType.REMOTE.value,
        )
    )
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=403, detail="无效的 Token")

    board.status = BoardStatus.ONLINE.value
    board.last_heartbeat = datetime.utcnow()
    await db.commit()

    return {"board_id": board.id, "name": board.name}


@router.get("/{board_id}/pending-commands")
async def get_pending_commands(board_id: int, db: AsyncSession = Depends(get_db)):
    """HTTP Agent 轮询获取待执行命令"""
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="板子不存在")

    board.last_heartbeat = datetime.utcnow()
    await db.commit()

    cmds = _pending_commands.pop(board_id, [])
    return {"commands": cmds}


@router.post("/{board_id}/command-result")
async def post_command_result(board_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """HTTP Agent 回传命令执行结果"""
    cmd_id = data.get("cmd_id", "")
    _command_results[cmd_id] = {
        "output": data.get("output", ""),
        "error": data.get("error", ""),
    }
    return {"success": True}
