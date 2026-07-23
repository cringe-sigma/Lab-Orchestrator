"""Agent Core — AI Agent 核心逻辑，与后端解耦的可复用层"""
from __future__ import annotations

import json
from typing import Any, Callable
from dataclasses import dataclass, field


@dataclass
class ExperimentStep:
    """实验单步定义"""
    step: int
    action: str  # exec_command / compile / flash / read_log / wait
    params: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    expected_result: str = ""
    timeout: int = 60


@dataclass
class ExperimentPlan:
    """实验计划"""
    name: str
    board_id: int
    description: str = ""
    steps: list[ExperimentStep] = field(default_factory=list)
    risk_level: str = "low"  # low / medium / high

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "board_id": self.board_id,
            "description": self.description,
            "steps": [
                {"step": s.step, "action": s.action, "params": s.params, "note": s.note}
                for s in self.steps
            ],
            "risk_level": self.risk_level,
        }


class ExperimentValidator:
    """实验计划校验器 — 在执行前检查安全性"""

    DANGEROUS_ACTIONS = {"flash_firmware", "dd", "reboot", "poweroff", "format", "mkfs"}
    READ_ONLY_COMMANDS = {"cat", "ls", "ps", "echo", "gcc", "make", "gdb", "top", "free", "df", "dmesg", "ifconfig", "ping -c", "uname", "lscpu", "lsof"}

    @classmethod
    def validate(cls, plan: ExperimentPlan) -> list[str]:
        """校验实验计划，返回警告列表"""
        warnings = []

        for step in plan.steps:
            action = step.action
            cmd = step.params.get("command", "")

            # 检查高危动作
            if action in cls.DANGEROUS_ACTIONS:
                warnings.append(f"步骤{step.step}: 高危操作 '{action}'，需要用户二次确认")

            # 检查高危命令关键词
            for dangerous in cls.DANGEROUS_ACTIONS:
                if dangerous in cmd:
                    warnings.append(f"步骤{step.step}: 命令包含高危关键词 '{dangerous}'")

            # 检查连续高危操作
            if step.timeout > 300:
                warnings.append(f"步骤{step.step}: 超时时间设为{step.timeout}秒，请确认实验不会卡死")

        if plan.risk_level == "high" and len(plan.steps) > 10:
            warnings.append("高风险实验步骤超过10步，建议拆分为多个子实验")

        return warnings


class ExecutionResult:
    """执行结果封装"""
    def __init__(self, success: bool, output: str, step_index: int, error: str = ""):
        self.success = success
        self.output = output
        self.step_index = step_index
        self.error = error

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "step_index": self.step_index,
            "error": self.error,
        }
