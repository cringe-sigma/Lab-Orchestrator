"""实验记录模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    board_id = Column(Integer, index=True, nullable=False)

    name = Column(String(200), nullable=False)
    description = Column(Text, default="")

    # 实验流程(AI生成的步骤)
    steps = Column(Text, default="")          # JSON: [{"step":1,"action":"..."}]
    status = Column(String(20), default="pending")  # pending/running/completed/failed

    # 结果
    result_summary = Column(Text, default="")
    result_data = Column(Text, default="")    # JSON
    log = Column(Text, default="")

    # 是否通过AI执行的
    is_ai_driven = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
