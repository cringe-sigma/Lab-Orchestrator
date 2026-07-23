"""AI Agent 调度器 — 对接 Anthropic SDK"""
from __future__ import annotations

import json
from typing import Any, Callable
from anthropic import AsyncAnthropic

from app.config import settings
from app.ai_agent.prompts import SYSTEM_PROMPT
from app.ai_agent.tools import TOOLS


class AIAgent:
    """AI Agent 主调度器"""

    def __init__(self):
        self.client: AsyncAnthropic | None = None
        self._tool_handlers: dict[str, Callable] = {}
        self._conversations: dict[str, list[dict]] = {}  # session_id → messages

        if settings.ANTHROPIC_API_KEY:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    def register_tool(self, name: str, handler: Callable):
        """注册工具的实际执行函数"""
        self._tool_handlers[name] = handler

    async def chat(self, session_id: str, user_message: str) -> str:
        """向 AI 发送消息并获取回复"""
        if not self.client:
            return "错误: Anthropic API 未配置，请在 .env 中设置 ANTHROPIC_API_KEY"

        if session_id not in self._conversations:
            self._conversations[session_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]

        self._conversations[session_id].append({"role": "user", "content": user_message})

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=self._conversations[session_id],
            tools=TOOLS,
        )

        assistant_content = ""
        for block in response.content:
            if block.type == "text":
                assistant_content += block.text
            elif block.type == "tool_use":
                tool_result = await self._execute_tool(block.name, block.input)
                assistant_content += f"\n[执行工具: {block.name}] 结果: {tool_result}\n"

        self._conversations[session_id].append({"role": "assistant", "content": assistant_content})
        return assistant_content

    async def _execute_tool(self, tool_name: str, params: dict) -> str:
        """执行 AI 请求的工具调用"""
        handler = self._tool_handlers.get(tool_name)
        if not handler:
            return f"错误: 未知工具 {tool_name}"
        try:
            result = await handler(**params)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return f"工具执行失败: {e}"

    def clear_conversation(self, session_id: str):
        self._conversations.pop(session_id, None)


# 全局单例
ai_agent = AIAgent()
