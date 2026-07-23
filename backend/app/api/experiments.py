"""实验管理 API"""
from __future__ import annotations

import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.experiment import Experiment
from app.models.user import User
from app.api.auth import get_current_user
from app.services.experiment_engine import ExperimentEngine
from app.ai_agent.agent import ai_agent

router = APIRouter(prefix="/api/experiments", tags=["实验管理"])


class StepSchema(BaseModel):
    step: int
    action: str
    params: dict = {}
    note: str = ""


class ExperimentCreate(BaseModel):
    board_id: int
    name: str
    description: str = ""
    steps: list[StepSchema] = []
    is_ai_driven: bool = False


class ExperimentResponse(BaseModel):
    id: int
    board_id: int
    name: str
    description: str
    steps: str
    status: str
    result_summary: str
    result_data: str
    is_ai_driven: bool
    created_at: str
    started_at: str | None
    completed_at: str | None


@router.get("/", response_model=list[ExperimentResponse])
async def list_experiments(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取实验列表"""
    from sqlalchemy import select
    result = await db.execute(
        select(Experiment).where(Experiment.user_id == user.id).order_by(Experiment.created_at.desc())
    )
    exps = result.scalars().all()
    return [
        ExperimentResponse(
            id=e.id, board_id=e.board_id, name=e.name, description=e.description or "",
            steps=e.steps or "[]", status=e.status,
            result_summary=e.result_summary or "", result_data=e.result_data or "",
            is_ai_driven=bool(e.is_ai_driven),
            created_at=e.created_at.isoformat() if e.created_at else "",
            started_at=e.started_at.isoformat() if e.started_at else None,
            completed_at=e.completed_at.isoformat() if e.completed_at else None,
        )
        for e in exps
    ]


@router.post("/", response_model=ExperimentResponse)
async def create_experiment(data: ExperimentCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """创建新实验"""
    exp = Experiment(
        user_id=user.id,
        board_id=data.board_id,
        name=data.name,
        description=data.description,
        steps=json.dumps([s.model_dump() for s in data.steps], ensure_ascii=False),
        status="pending",
        is_ai_driven=1 if data.is_ai_driven else 0,
    )
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return await _exp_to_response(exp)


@router.get("/{exp_id}", response_model=ExperimentResponse)
async def get_experiment(exp_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    exp = await db.get(Experiment, exp_id)
    if not exp or exp.user_id != user.id:
        raise HTTPException(status_code=404, detail="实验不存在")
    return await _exp_to_response(exp)


@router.post("/{exp_id}/run")
async def run_experiment(exp_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """执行实验所有步骤"""
    exp = await db.get(Experiment, exp_id)
    if not exp or exp.user_id != user.id:
        raise HTTPException(status_code=404, detail="实验不存在")

    engine = ExperimentEngine(db)
    results = await engine.run_all(exp_id)
    return {"results": results}


@router.post("/{exp_id}/step/{step_index}")
async def run_step(exp_id: int, step_index: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """执行单步"""
    exp = await db.get(Experiment, exp_id)
    if not exp or exp.user_id != user.id:
        raise HTTPException(status_code=404, detail="实验不存在")

    engine = ExperimentEngine(db)
    result = await engine.run_step(exp_id, step_index)
    return result


@router.post("/ai-chat/{board_id}")
async def ai_chat(board_id: int, data: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """与 AI Agent 对话，让 AI 帮你操作板子"""
    message = data.get("message", "")
    session_id = f"user_{user.id}_board_{board_id}"

    # 注册 AI 可用的工具处理器
    from app.services.board_manager import board_manager as bm
    from app.services.experiment_engine import ExperimentEngine
    from app.models.board import Board

    async def handle_exec_command(board_id: int, command: str) -> dict:
        board = await db.get(Board, board_id)
        if not board:
            return {"error": "板子不存在"}
        output = await bm.exec_on_board(board, command)
        return {"output": output}

    async def handle_list_boards() -> dict:
        from sqlalchemy import select
        result = await db.execute(select(Board).where(Board.is_active == True))
        boards = result.scalars().all()
        return {"boards": [{"id": b.id, "name": b.name, "status": b.status} for b in boards]}

    async def handle_check_board_status(board_id: int) -> dict:
        board = await db.get(Board, board_id)
        if not board:
            return {"error": "板子不存在"}
        return {"id": board.id, "name": board.name, "status": board.status, "locked_by": board.locked_by}

    async def handle_create_experiment_plan(board_id: int, name: str, steps: list, description: str = "") -> dict:
        exp = Experiment(
            user_id=user.id, board_id=board_id, name=name,
            description=description,
            steps=json.dumps(steps, ensure_ascii=False),
            status="pending",
            is_ai_driven=1,
        )
        db.add(exp)
        await db.commit()
        await db.refresh(exp)
        return {"experiment_id": exp.id, "name": name, "step_count": len(steps), "status": "待确认"}

    async def handle_compile_source(board_id: int, source_path: str, build_command: str) -> dict:
        board = await db.get(Board, board_id)
        if not board:
            return {"error": "板子不存在"}
        output = await bm.exec_on_board(board, f"cd {source_path} && {build_command}")
        return {"output": output}

    async def handle_flash_firmware(board_id: int, firmware_path: str, tool: str = "") -> dict:
        return {"warning": "高危操作已阻止", "message": "固件烧录需要用户二次确认，请在界面上手动操作"}

    async def handle_read_log(board_id: int, file_path: str) -> dict:
        board = await db.get(Board, board_id)
        if not board:
            return {"error": "板子不存在"}
        output = await bm.exec_on_board(board, f"cat {file_path}")
        return {"content": output}

    async def handle_run_experiment_step(experiment_id: int, step_index: int) -> dict:
        engine = ExperimentEngine(db)
        result = await engine.run_step(experiment_id, step_index)
        return result

    # 注册所有工具
    ai_agent.register_tool("exec_command", handle_exec_command)
    ai_agent.register_tool("list_boards", handle_list_boards)
    ai_agent.register_tool("check_board_status", handle_check_board_status)
    ai_agent.register_tool("create_experiment_plan", handle_create_experiment_plan)
    ai_agent.register_tool("compile_source", handle_compile_source)
    ai_agent.register_tool("flash_firmware", handle_flash_firmware)
    ai_agent.register_tool("read_log", handle_read_log)
    ai_agent.register_tool("run_experiment_step", handle_run_experiment_step)

    reply = await ai_agent.chat(session_id, message)
    return {"reply": reply}


async def _exp_to_response(exp: Experiment) -> ExperimentResponse:
    return ExperimentResponse(
        id=exp.id, board_id=exp.board_id, name=exp.name, description=exp.description or "",
        steps=exp.steps or "[]", status=exp.status,
        result_summary=exp.result_summary or "", result_data=exp.result_data or "",
        is_ai_driven=bool(exp.is_ai_driven),
        created_at=exp.created_at.isoformat() if exp.created_at else "",
        started_at=exp.started_at.isoformat() if exp.started_at else None,
        completed_at=exp.completed_at.isoformat() if exp.completed_at else None,
    )
