"""预约调度引擎"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.board import Board, BoardStatus


class Scheduler:
    """预约调度 & 板子排他控制"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_board_available(self, board_id: int, start: datetime, end: datetime) -> bool:
        """检查板子在时间段内是否可用"""
        stmt = select(Booking).where(
            and_(
                Booking.board_id == board_id,
                Booking.status.in_(["pending", "active"]),
                Booking.start_time < end,
                Booking.end_time > start,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is None

    async def create_booking(
        self, user_id: int, board_id: int, title: str,
        start: datetime, end: datetime
    ) -> dict:
        """创建预约"""
        available = await self.is_board_available(board_id, start, end)
        if not available:
            return {"success": False, "message": "该时段板子已被预约"}

        booking = Booking(
            user_id=user_id,
            board_id=board_id,
            title=title,
            start_time=start,
            end_time=end,
            status="pending",
        )
        self.db.add(booking)
        await self.db.commit()
        await self.db.refresh(booking)
        return {"success": True, "booking_id": booking.id}

    async def activate_booking(self, booking_id: int) -> bool:
        """激活预约(到开始时间时调用)"""
        booking = await self.db.get(Booking, booking_id)
        if not booking or booking.status != "pending":
            return False
        booking.status = "active"
        await self.db.commit()
        return True

    async def complete_booking(self, booking_id: int):
        """完成预约"""
        booking = await self.db.get(Booking, booking_id)
        if booking:
            booking.status = "completed"
            await self.db.commit()

    async def cancel_booking(self, booking_id: int):
        """取消预约"""
        booking = await self.db.get(Booking, booking_id)
        if booking:
            booking.status = "cancelled"
            await self.db.commit()

    async def get_user_bookings(self, user_id: int) -> list[Booking]:
        stmt = select(Booking).where(Booking.user_id == user_id).order_by(Booking.start_time)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
