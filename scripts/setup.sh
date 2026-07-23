#!/bin/bash
# Lab Orchestrator — 一键初始化
set -e

echo "=== Lab Orchestrator 初始化 ==="

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python 3.10+"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 需要 Node.js 18+"
    exit 1
fi

# 后端
echo ""
echo ">>> 安装后端依赖..."
cd "$(dirname "$0")/../backend"
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true
pip install -r requirements.txt

# .env
if [ ! -f .env ]; then
    echo "ANTHROPIC_API_KEY=your-key-here" > .env
    echo "SECRET_KEY=dev-secret-key-change-in-production" >> .env
    echo ">>> 已创建 .env 文件，请配置 ANTHROPIC_API_KEY"
fi

# 前端
echo ""
echo ">>> 安装前端依赖..."
cd ../frontend
npm install

echo ""
echo "========================================"
echo "✅ 初始化完成！启动方式："
echo ""
echo "  终端 1 - 后端:"
echo "    cd backend && source .venv/bin/activate"
echo "    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "  终端 2 - 前端:"
echo "    cd frontend && npm run dev"
echo ""
echo "  访问: http://localhost:5173"
echo "========================================"
