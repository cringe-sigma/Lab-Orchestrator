# Lab Orchestrator — CLAUDE.md (AI开发约束)

## 项目核心规则（不可违背）

1. **AI Agent 只能执行纯软件操作** — 不允许涉及硬件接线、电压测量、电源控制等物理操作。所有 AI 的操作必须经过工具函数封装，AI 不能自由编写 shell 命令执行。
2. **高危操作双重确认** — 涉及固件烧录、系统重启、文件删除的操作，必须先输出步骤计划，弹窗让用户手动输入 "我确认执行" 才能继续。
3. **板子操作必须有锁** — 同一时间只有一个人/AI 能控制一块板子，后端代码硬性控制排他，不由 AI 判断。
4. **所有操作可审计** — 每次 AI 调用、每次 SSH 操作、每次实验运行都必须记录日志（谁、什么时间、对哪块板子、做了什么）。

## 技术选型（约定不可随意更改）

| 层级 | 技术 | 版本约束 |
|------|------|---------|
| 后端框架 | FastAPI | >=0.110 |
| 数据库 | SQLite (dev) / PostgreSQL (prod) | — |
| 前端框架 | Vue 3 + TypeScript + Vite | Vue >=3.4 |
| AI SDK | Anthropic Python SDK | >=0.40 |
| SSH 连接 | asyncssh | >=2.14 |
| 串口通信 | pyserial | >=3.5 |

## 编码规范

- 后端：类型注解必须完整，所有 API 用 Pydantic model 做输入输出校验
- 前端：组件使用 Composition API + `<script setup>` 语法
- 所有新功能必须先写 API 再对接前端
- 错误信息必须中文（用户群体是中文使用者）

## 目录职责

- `backend/` — FastAPI 后端，提供 REST API
- `frontend/` — Vue 3 前端
- `agent-core/` — AI Agent 核心逻辑，与后端解耦
- `docs/` — 架构设计、扩展方案文档
- `hardware/` — 硬件采购和扩展方案
- `scripts/` — 快捷脚本

## Git 提交规范

- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- chore: 构建/工具
