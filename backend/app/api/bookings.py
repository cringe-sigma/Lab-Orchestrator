"""预约管理 API"""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.booking import Booking
from app.models.user import User
from app.api.auth import get_current_user
from app.services.scheduler import Scheduler

router = APIRouter(prefix="/api/bookings", tags=["预约管理"])


class BookingCreate(BaseModel):
    board_id: int
    title: str = ""
    start_time: str  # ISO 格式
    end_time: str


class BookingResponse(BaseModel):
    id: int
    board_id: int
    title: str
    start_time: str
    end_time: str
    status: str
    created_at: str


@router.get("/", response_model=list[BookingResponse])
async def list_bookings(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取当前用户的预约"""
    scheduler = Scheduler(db)
    bookings = await scheduler.get_user_bookings(user.id)
    return [
        BookingResponse(
            id=b.id, board_id=b.board_id, title=b.title or "",
            start_time=b.start_time.isoformat() if b.start_time else "",
            end_time=b.end_time.isoformat() if b.end_time else "",
            status=b.status,
            created_at=b.created_at.isoformat() if b.created_at else "",
        )
        for b in bookings
    ]


@router.post("/")
async def create_booking(data: BookingCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """创建预约"""
    start = datetime.fromisoformat(data.start_time)
    end = datetime.fromisoformat(data.end_time)

    if start >= end:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
    if start < datetime.utcnow():
        raise HTTPException(status_code=400, detail="不能预约过去的时间")

    scheduler = Scheduler(db)
    result = await scheduler.create_booking(user.id, data.board_id, data.title, start, end)

    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return result


@router.post("/{booking_id}/cancel")
async def cancel_booking(booking_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """取消预约"""
    booking = await db.get(Booking, booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="预约已结束或已取消")

    scheduler = Scheduler(db)
    await scheduler.cancel_booking(booking_id)
    return {"success": True}
