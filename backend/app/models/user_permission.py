"""细粒度权限覆写模型 — 管理员可对任意用户增删独立权限"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.db.database import Base


class UserPermissionOverride(Base):
    """个人权限覆写表

    每个用户继承其角色的默认权限，此表记录个体覆写:
    - grant  = 额外授予一项权限(角色默认没有的)
    - revoke = 收回一项权限(角色默认有的)
    """

    __tablename__ = "user_permission_overrides"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    permission_key = Column(String(50), nullable=False)
    action = Column(String(10), nullable=False)  # "grant" | "revoke"
    granted_by = Column(Integer, nullable=False)  # admin user_id
    created_at = Column(DateTime, default=datetime.utcnow)
