"""应用配置"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "Lab Orchestrator"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./lab_orchestrator.db"

    # JWT
    SECRET_KEY: str = "change-this-to-a-strong-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8小时

    # Anthropic API (AI Agent)
    ANTHROPIC_API_KEY: str = ""

    # 板子连接默认超时(秒)
    BOARD_SSH_TIMEOUT: int = 30
    BOARD_SERIAL_TIMEOUT: int = 10

    # 预约
    BOOKING_MAX_DURATION_HOURS: int = 4
    BOOKING_GRACE_MINUTES: int = 10  # 预约超时保留时间

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
