#!/bin/bash
# Lab Orchestrator — 快速启动演示
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

echo "=== 启动 Lab Orchestrator ==="

# 启动后端（后台）
echo ">>> 启动后端..."
cd "$BACKEND_DIR"
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 启动前端（后台）
echo ">>> 启动前端..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

echo ""
echo "========================================"
echo "✅ 服务已启动"
echo "   后端: http://localhost:8000"
echo "   前端: http://localhost:5173"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "========================================"

# 等待任意进程退出
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
