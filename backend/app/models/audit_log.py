"""板子操作审计日志"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.database import Base


class BoardAuditLog(Base):
    __tablename__ = "board_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(50), default="")
    action = Column(String(20), nullable=False)  # create / delete
    board_id = Column(Integer, nullable=True)
    board_name = Column(String(100), default="")
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
