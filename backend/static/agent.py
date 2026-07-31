"""
Board Agent — 运行在远程板子上的代理程序

功能: 主动连接服务器 → 注册板子 → 接收命令 → 执行 → 返回结果
适用: Raspberry Pi / Jetson / Orange Pi / 任何有 Python 的 Linux 板子

启动方式:
    python agent.py --server ws://192.168.1.100:8000/ws/board --token BOARD_TOKEN

依赖: pip install websockets
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import time


class BoardAgent:
    """远程板子代理 — 运行在板子上"""

    def __init__(self, server_url: str, board_token: str):
        self.server_url = server_url
        self.board_token = board_token
        self._ws = None
        self._running = False

        # 收集板子基本信息
        self.board_info = {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python_version": sys.version,
            "started_at": time.time(),
        }

    async def start(self):
        """启动代理，连接服务器"""
        self._running = True
        print(f"[Agent] 正在连接服务器: {self.server_url}")

        import websockets

        while self._running:
            try:
                async with websockets.connect(
                    self.server_url,
                    extra_headers={"Authorization": f"Bearer {self.board_token}"},
                    ping_interval=30,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    print("[Agent] 已连接到服务器")

                    # 发送注册信息
                    await ws.send(json.dumps({
                        "type": "register",
                        "board_info": self.board_info,
                    }))
                    register_resp = await ws.recv()
                    reg_data = json.loads(register_resp)
                    print(f"[Agent] 注册成功: board_id={reg_data.get('board_id')}")

                    # 监听命令循环
                    async for raw_msg in ws:
                        await self._handle_message(raw_msg)

            except Exception as e:
                print(f"[Agent] 连接断开: {e}")
                if self._running:
                    print("[Agent] 5秒后重连...")
                    await asyncio.sleep(5)

    async def _handle_message(self, raw_msg: str):
        """处理服务器发来的消息"""
        try:
            msg = json.loads(raw_msg)
        except json.JSONDecodeError:
            return

        msg_type = msg.get("type")

        if msg_type == "execute":
            cmd_id = msg.get("cmd_id")
            command = msg.get("command", "")
            timeout = msg.get("timeout", 60)

            print(f"[Agent] 执行命令: {command}")
            result = await self._run_command(command, timeout)
            await self._ws.send(json.dumps({
                "type": "result",
                "cmd_id": cmd_id,
                "output": result["output"],
                "exit_code": result["exit_code"],
            }))

        elif msg_type == "heartbeat":
            await self._ws.send(json.dumps({
                "type": "heartbeat_ack",
                "info": self.board_info,
            }))

        elif msg_type == "shutdown":
            print("[Agent] 服务器要求关闭")
            await self.stop()

    async def _run_command(self, command: str, timeout: int) -> dict:
        """在板子上执行命令"""
        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                ),
                timeout=timeout,
            )
            stdout, _ = await proc.communicate()
            return {
                "output": stdout.decode(errors="replace"),
                "exit_code": proc.returncode or 0,
            }
        except asyncio.TimeoutError:
            return {"output": f"命令超时({timeout}s)", "exit_code": -1}
        except Exception as e:
            return {"output": str(e), "exit_code": -1}

    async def stop(self):
        """停止代理"""
        self._running = False
        if self._ws:
            await self._ws.close()
        print("[Agent] 已停止")


def main():
    parser = argparse.ArgumentParser(description="Lab Orchestrator Board Agent")
    parser.add_argument("--server", required=True, help="服务器 WebSocket 地址")
    parser.add_argument("--token", required=True, help="板子认证 Token")
    args = parser.parse_args()

    agent = BoardAgent(server_url=args.server, board_token=args.token)

    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("\n[Agent] Ctrl+C 收到，正在关闭...")
        asyncio.run(agent.stop())


if __name__ == "__main__":
    main()
