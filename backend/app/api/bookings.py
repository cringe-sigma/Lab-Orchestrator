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
    from datetime import timezone
    start = datetime.fromisoformat(data.start_time)
    end = datetime.fromisoformat(data.end_time)

    # 如无时区信息，假定为 UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if start >= end:
        raise HTTPException(status_code=400, detail="开始时间必须早于结束时间")
    if start < datetime.now(timezone.utc):
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


@router.post("/{booking_id}/share")
async def share_booking(booking_id: int, data: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """共享预约给其他用户"""
    booking = await db.get(Booking, booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="预约已取消")

    import json as _json
    shared = _json.loads(booking.shared_with or "[]")
    new_user_ids = data.get("user_ids", [])
    for uid in new_user_ids:
        if uid not in shared:
            shared.append(uid)
    booking.shared_with = _json.dumps(shared)
    await db.commit()
    return {"success": True, "shared_with": shared}


# 全板子预约时间表 (用于日历视图)
@router.get("/schedule")
async def get_schedule(date: str = "", db: AsyncSession = Depends(get_db)):
    """获取指定日期的所有板子预约时间表 (30分钟粒度)"""
    from datetime import timezone, timedelta
    if not date:
        d = datetime.now(timezone.utc)
    else:
        d = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)

    day_start = d.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    result = await db.execute(
        select(Booking).where(
            Booking.start_time < day_end,
            Booking.end_time > day_start,
            Booking.status.in_(["pending", "active"]),
        )
    )
    bookings = result.scalars().all()

    slots = []
    for b in bookings:
        slots.append({
            "id": b.id,
            "board_id": b.board_id,
            "title": b.title,
            "start": b.start_time.isoformat() if b.start_time else "",
            "end": b.end_time.isoformat() if b.end_time else "",
            "status": b.status,
            "user_id": b.user_id,
        })
    return {"slots": slots}
