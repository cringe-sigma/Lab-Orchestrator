"""实验执行引擎"""
from __future__ import annotations

import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import Experiment
from app.models.board import Board
from app.services.board_manager import board_manager


class ExperimentEngine:
    """执行实验步骤序列"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_step(self, experiment_id: int, step_index: int) -> dict:
        """执行单步实验"""
        exp = await self.db.get(Experiment, experiment_id)
        if not exp:
            return {"success": False, "error": "实验不存在"}

        steps = json.loads(exp.steps or "[]")
        if step_index >= len(steps):
            return {"success": False, "error": "步骤索引超出范围"}

        step = steps[step_index]
        board = await self.db.get(Board, exp.board_id)
        if not board:
            return {"success": False, "error": "板子不存在"}

        action = step.get("action", "")
        params = step.get("params", {})

        if board.conn_type == "ssh":
            command = params.get("command", "")
            output = await board_manager.exec_on_board(board, command)
        elif board.conn_type == "serial":
            # 串口实验逻辑
            output = "串口实验待实现"
        else:
            output = "不支持的连接类型"

        step["result"] = output
        step["status"] = "done"
        steps[step_index] = step
        exp.steps = json.dumps(steps, ensure_ascii=False)

        # 如果是最后一步，标记完成
        if step_index == len(steps) - 1:
            exp.status = "completed"
            exp.completed_at = datetime.utcnow()
        else:
            exp.status = "running"
            exp.started_at = exp.started_at or datetime.utcnow()

        await self.db.commit()
        return {"success": True, "step": step, "output": output}

    async def run_all(self, experiment_id: int) -> list[dict]:
        """顺序执行所有步骤"""
        exp = await self.db.get(Experiment, experiment_id)
        if not exp:
            return [{"error": "实验不存在"}]

        steps = json.loads(exp.steps or "[]")
        results = []

        for i in range(len(steps)):
            result = await self.run_step(experiment_id, i)
            results.append(result)
            if not result.get("success"):
                break

        return results
