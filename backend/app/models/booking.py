"""预约模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    board_id = Column(Integer, index=True, nullable=False)

    title = Column(String(200), default="")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")  # pending/active/completed/cancelled/expired

    created_at = Column(DateTime, default=datetime.utcnow)
