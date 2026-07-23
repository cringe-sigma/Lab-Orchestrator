# Lab Orchestrator

远程嵌入式实验编排平台。通过 Web 界面 + AI Agent 远程管理多块嵌入式板子，支持预约、实验自动化、结果分析。

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## 架构

```
用户(浏览器) ←→ Vue 3 Frontend ←→ FastAPI Backend ←→ AI Agent
                              ↕                    ↕
                          SQLite/PostgreSQL     Board Pool (SSH/Serial)
```

## 项目结构

```
backend/       — FastAPI API 服务
frontend/      — Vue 3 管理界面
agent-core/    — AI Agent 逻辑
docs/          — 架构文档 & 扩展方案
hardware/      — 硬件采购清单 & 拓扑
scripts/       — 部署脚本
```

详见 [docs/architecture.md](docs/architecture.md)
