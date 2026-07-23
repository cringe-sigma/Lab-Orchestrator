"""板子模型"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from app.db.database import Base
import enum


class BoardType(str, enum.Enum):
    LINUX = "linux"       # 树莓派/Jetson/BeagleBone 等
    MCU = "mcu"           # STM32/ESP32 等裸机


class BoardStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class ConnType(str, enum.Enum):
    SSH = "ssh"
    SERIAL = "serial"


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    board_type = Column(String(20), default=BoardType.LINUX.value)
    status = Column(String(20), default=BoardStatus.OFFLINE.value)

    # 连接信息
    conn_type = Column(String(20), default=ConnType.SSH.value)
    host = Column(String(255), nullable=True)       # SSH IP
    port = Column(Integer, default=22)               # SSH port
    username = Column(String(100), nullable=True)    # SSH 用户名
    serial_port = Column(String(100), nullable=True) # 串口路径(如 COM3)
    serial_baud = Column(Integer, default=115200)    # 串口波特率

    # 标签 & 描述
    tags = Column(Text, default="")                  # JSON 数组
    description = Column(Text, default="")

    # 当前占用者
    locked_by = Column(Integer, nullable=True)       # user_id
    locked_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime, nullable=True)
