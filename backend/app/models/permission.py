"""权限申请模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.database import Base


class PermissionRequest(Base):
    """用户权限申请记录"""

    __tablename__ = "permission_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    requested_role = Column(String(20), nullable=False)  # admin / user / viewer
    reason = Column(Text, default="")
    status = Column(String(20), default="pending")  # pending / approved / rejected
    reviewed_by = Column(Integer, nullable=True)  # 审批者 user_id
    review_comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
