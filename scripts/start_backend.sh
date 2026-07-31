#!/bin/bash
# Lab Orchestrator Backend — 持久化启动 (不删除数据库)
cd "$(dirname "$0")/../backend"
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null

echo "Starting Lab Orchestrator (DB preserved)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
