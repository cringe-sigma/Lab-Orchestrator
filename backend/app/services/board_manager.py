"""板子连接池管理"""
from __future__ import annotations

import asyncio
import asyncssh
import serial
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board import Board, BoardStatus


class BoardConnection:
    """单块板子的连接封装"""

    def __init__(self, board: Board):
        self.board_id = board.id
        self.conn_type = board.conn_type
        self._ssh: Optional[asyncssh.SSHClientConnection] = None
        self._serial: Optional[serial.Serial] = None
        self._lock = asyncio.Lock()
        self._host = board.host
        self._port = board.port
        self._username = board.username
        self._serial_port = board.serial_port
        self._serial_baud = board.serial_baud

    async def connect(self, password: str = "") -> bool:
        """建立连接"""
        try:
            if self.conn_type == "ssh" and self._host:
                self._ssh = await asyncssh.connect(
                    self._host,
                    port=self._port or 22,
                    username=self._username,
                    password=password or None,
                    known_hosts=None,
                    connect_timeout=30,
                )
                return True
            elif self.conn_type == "serial" and self._serial_port:
                self._serial = serial.Serial(
                    port=self._serial_port,
                    baudrate=self._serial_baud or 115200,
                    timeout=10,
                )
                return True
        except Exception as e:
            print(f"[BoardConnection] 连接失败 board={self.board_id}: {e}")
        return False

    async def disconnect(self):
        async with self._lock:
            if self._ssh:
                self._ssh.close()
                self._ssh = None
            if self._serial and self._serial.is_open:
                self._serial.close()
                self._serial = None

    async def exec(self, command: str) -> str:
        """执行命令(SSH)"""
        async with self._lock:
            if not self._ssh:
                return "错误: SSH 未连接"
            result = await self._ssh.run(command, timeout=60)
            return result.stdout or result.stderr or ""

    async def write_serial(self, data: str) -> str:
        """写串口并读取返回"""
        async with self._lock:
            if not self._serial or not self._serial.is_open:
                return "错误: 串口未连接"
            self._serial.write(data.encode())
            await asyncio.sleep(0.1)
            response = self._serial.read_all().decode(errors="replace")
            return response or ""

    @property
    def is_connected(self) -> bool:
        if self._ssh and self._ssh.is_active:
            return True
        if self._serial and self._serial.is_open:
            return True
        return False


class BoardManager:
    """板子连接管理器 - 全局单例"""

    def __init__(self):
        self._connections: dict[int, BoardConnection] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, board: Board, password: str = "") -> BoardConnection:
        async with self._lock:
            conn = self._connections.get(board.id)
            if conn and conn.is_connected:
                return conn
            conn = BoardConnection(board)
            ok = await conn.connect(password)
            if ok:
                self._connections[board.id] = conn
            return conn

    async def disconnect(self, board_id: int):
        async with self._lock:
            conn = self._connections.pop(board_id, None)
            if conn:
                await conn.disconnect()

    async def disconnect_all(self):
        async with self._lock:
            for conn in self._connections.values():
                await conn.disconnect()
            self._connections.clear()

    async def exec_on_board(self, board: Board, command: str, password: str = "") -> str:
        conn = await self.get_or_create(board, password)
        return await conn.exec(command)

    async def check_health(self, board: Board, password: str = "") -> BoardStatus:
        """检查板子状态"""
        try:
            conn = await self.get_or_create(board, password)
            if self._check_ssh_ok(conn):
                return BoardStatus.ONLINE
            return BoardStatus.OFFLINE
        except Exception:
            return BoardStatus.OFFLINE

    def _check_ssh_ok(self, conn: BoardConnection) -> bool:
        return conn.is_connected


# 全局单例
board_manager = BoardManager()
