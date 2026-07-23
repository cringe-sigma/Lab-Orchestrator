"""AI Agent 可调用的工具函数"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """工具定义，用于告知 AI 可用的函数"""
    name: str
    description: str
    parameters: dict[str, Any]


# ========== 工具定义（Anthropic Tool Use 格式） ==========

TOOLS = [
    {
        "name": "exec_command",
        "description": "在指定板子上执行 shell 命令（只读操作，如 cat/ls/ps/gcc/test）",
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "板子ID"},
                "command": {"type": "string", "description": "要执行的 shell 命令"},
            },
            "required": ["board_id", "command"],
        },
    },
    {
        "name": "run_experiment_step",
        "description": "执行实验的某个步骤（需要先创建实验计划）",
        "input_schema": {
            "type": "object",
            "properties": {
                "experiment_id": {"type": "integer", "description": "实验ID"},
                "step_index": {"type": "integer", "description": "步骤序号(从0开始)"},
            },
            "required": ["experiment_id", "step_index"],
        },
    },
    {
        "name": "flash_firmware",
        "description": "烧录固件到板子（高危操作，需要用户二次确认）",
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "板子ID"},
                "firmware_path": {"type": "string", "description": "固件文件路径"},
                "tool": {"type": "string", "description": "烧录工具"},
            },
            "required": ["board_id", "firmware_path"],
        },
    },
    {
        "name": "compile_source",
        "description": "在板子上编译源代码",
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "板子ID"},
                "source_path": {"type": "string", "description": "源码路径"},
                "build_command": {"type": "string", "description": "编译命令，如 'make' 或 'gcc main.c -o test'"},
            },
            "required": ["board_id", "source_path", "build_command"],
        },
    },
    {
        "name": "check_board_status",
        "description": "检查板子在线状态和占用情况",
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "板子ID"},
            },
            "required": ["board_id"],
        },
    },
    {
        "name": "list_boards",
        "description": "列出用户可用的所有板子",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_experiment_plan",
        "description": "创建实验计划（步骤序列），创建后展示给用户确认",
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "目标板子ID"},
                "name": {"type": "string", "description": "实验名称"},
                "description": {"type": "string", "description": "实验描述"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "integer"},
                            "action": {"type": "string"},
                            "params": {"type": "object"},
                            "note": {"type": "string"},
                        },
                    },
                    "description": "实验步骤列表",
                },
            },
            "required": ["board_id", "name", "steps"],
        },
    },
    {
        "name": "read_log",
        "description": "读取板子上指定文件的内容（如日志）",
        "input_schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "板子ID"},
                "file_path": {"type": "string", "description": "文件路径"},
            },
            "required": ["board_id", "file_path"],
        },
    },
]
