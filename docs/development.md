# Lab Orchestrator — 开发运维指南

> 管理员专用文档，涵盖后端开发、维护和排障。

---

## 目录

1. [项目架构](#1-项目架构)
2. [环境配置](#2-环境配置)
3. [数据库管理](#3-数据库管理)
4. [添加新 API](#4-添加新-api)
5. [添加新板子类型](#5-添加新板子类型)
6. [AI Agent 扩展](#6-ai-agent-扩展)
7. [运维命令](#7-运维命令)
8. [排障指南](#8-排障指南)

---

## 1. 项目架构

```
backend/
├── app/
│   ├── main.py              ← FastAPI 应用入口，注册路由和中间件
│   ├── config.py            ← 所有配置项（从 .env 读取）
│   ├── api/                 ← API 路由层
│   │   ├── auth.py          ─ 认证（注册/登录/JWT）
│   │   ├── boards.py        ─ 板子 CRUD + 命令执行
│   │   ├── experiments.py   ─ 实验管理 + AI 对话
│   │   └── bookings.py      ─ 预约排期
│   ├── models/              ← SQLAlchemy 数据模型
│   │   ├── user.py          ─ 用户
│   │   ├── board.py         ─ 板子（支持 SSH 和串口）
│   │   ├── experiment.py    ─ 实验记录
│   │   └── booking.py       ─ 预约
│   ├── services/            ← 业务逻辑层
│   │   ├── board_manager.py ─ 板子连接池（SSH/串口管理）
│   │   ├── scheduler.py     ─ 预约调度引擎
│   │   └── experiment_engine.py ─ 实验执行引擎
│   ├── ai_agent/            ← AI Agent 模块
│   │   ├── agent.py         ─ Anthropic SDK 调度器
│   │   ├── tools.py         ─ AI 可调用的工具定义
│   │   └── prompts.py       ─ 系统提示词
│   └── db/
│       └── database.py      ← 数据库初始化
└── requirements.txt
```

**核心原则：** `api/` 只做请求/响应处理，业务逻辑下沉到 `services/`。

---

## 2. 环境配置

### 2.1 .env 文件

后端根目录下创建 `.env`：

```ini
# 必填 — Anthropic API 密钥（AI 助手功能需要）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# 可选 — JWT 签名密钥（生产环境务必更换）
SECRET_KEY=your-strong-secret-key-here

# 可选 — 切换到 PostgreSQL（默认 SQLite）
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/lab_orchestrator

# 可选 — 调试模式
DEBUG=true
```

### 2.2 数据库初始化

```bash
# 启动时自动建表（main.py 的 lifespan 中调用 init_db()）
# 如需手动重建：
python -c "
import asyncio
from app.db.database import init_db
asyncio.run(init_db())
"
```

---

## 3. 数据库管理

### 3.1 默认 SQLite

数据库文件生成在 `backend/` 目录下 `lab_orchestrator.db`。

```bash
# 查看数据（调试用）
sqlite3 lab_orchestrator.db ".tables"
sqlite3 lab_orchestrator.db "SELECT * FROM users;"
```

### 3.2 切换到 PostgreSQL

1. 安装：`pip install asyncpg`
2. 修改 `.env` 中的 `DATABASE_URL`
3. 确保 PostgreSQL 已运行且有对应数据库

### 3.3 添加新字段

1. 在对应的 `models/*.py` 中添加 Column
2. **生产环境**使用 Alembic 做迁移（当前项目未集成，需要时执行下面命令）：

```bash
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "add new field"
alembic upgrade head
```

### 3.4 插入初始管理员账号

```python
# scripts/create_admin.py
import asyncio
from app.db.database import async_session_factory, init_db
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

async def main():
    await init_db()
    async with async_session_factory() as session:
        admin = User(
            username="admin",
            hashed_password=pwd_context.hash("admin123"),
            display_name="管理员",
            role="admin",
        )
        session.add(admin)
        await session.commit()
        print("管理员账号创建成功: admin / admin123")

asyncio.run(main())
```

---

## 4. 添加新 API

### 步骤

1. 在 `app/api/` 下创建新的路由文件（参考已有文件的结构）：

```python
from fastapi import APIRouter, Depends
from app.db.database import get_db
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/your-resource", tags=["资源名称"])

@router.get("/")
async def list_all(db=Depends(get_db), user: User = Depends(get_current_user)):
    # user 是当前登录用户，已经过 JWT 认证
    return {"message": "new api"}
```

2. 在 `app/main.py` 中注册路由：

```python
from app.api import your_new_module
app.include_router(your_new_module.router)
```

3. 在前端 `api/client.ts` 中添加对应的 API 调用函数。

---

## 5. 添加新板子类型

在 `app/models/board.py` 的 `BoardType` 枚举中新增：

```python
class BoardType(str, enum.Enum):
    LINUX = "linux"
    MCU = "mcu"
    NEW_TYPE = "new_type"  # 新增
```

然后在 `app/services/board_manager.py` 的 `BoardConnection` 中处理新的连接协议。

---

## 6. AI Agent 扩展

### 添加新的工具函数

1. 在 `app/ai_agent/tools.py` 的 `TOOLS` 列表中添加工具定义。
2. 在 `app/api/experiments.py` 的 `ai_chat` 函数中注册对应的处理函数。
3. 在 `app/ai_agent/agent.py` 的 `_execute_tool` 中会自动分发。

### 修改系统提示词

编辑 `app/ai_agent/prompts.py` 中的 `SYSTEM_PROMPT`。

### 添加实验模板

在 `agent-core/experiment_planner.py` 中添加新的工厂函数，并注册到 `EXPERIMENT_TEMPLATES`。

---

## 7. 运维命令

### 启动（开发）

```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--reload` 会自动检测代码修改重启，开发时使用。

### 启动（生产）

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

建议配合 `gunicorn` + `uvicorn workers` 使用。

### 查看 API 文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 日志

FastAPI 默认将日志输出到 stdout。如需持久化，在启动时重定向：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee -a logs/app.log
```

---

## 8. 排障指南

### 后端无法启动

| 症状 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |
| `Address already in use` | 端口被占用 | 换端口或 `kill` 占用进程 |
| `Cannot connect to database` | 数据库路径错误 | 检查 `.env` 的 `DATABASE_URL` |
| `ImportError` | Python 版本不对 | 需要 Python 3.10+ |

### 板子连接失败

| 症状 | 原因 | 解决 |
|------|------|------|
| SSH 超时 | IP 不对/板子关机 | 在板子管理页面点击"检查" |
| 认证失败 | 密码错误 | 检查 SSH 用户名和密码 |
| 串口打不开 | 端口被占用 | 关闭其他串口监视器(如 PuTTY) |
| 串口乱码 | 波特率不匹配 | 核对板子的实际波特率 |

### AI 助手不工作

| 症状 | 原因 | 解决 |
|------|------|------|
| "API 未配置" | 缺少 KEY | 在 `.env` 中设置 `ANTHROPIC_API_KEY` |
| 401 Unauthorized | KEY 无效 | 检查 API Key 是否正确 |
| Rate limit | 调用超限 | 等待 1 分钟后重试 |

### 数据库问题

```bash
# SQLite 损坏修复
sqlite3 lab_orchestrator.db ".recover" | sqlite3 recovered.db
mv recovered.db lab_orchestrator.db

# 数据迁移备份
cp lab_orchestrator.db lab_orchestrator.db.bak.$(date +%Y%m%d)
```

---

## 附录：常用命令速查

```bash
# 后端
pip install -r requirements.txt     # 安装依赖
uvicorn app.main:app --reload       # 启动开发服务器

# 前端
npm install                         # 安装依赖
npm run dev                         # 启动开发服务器
npm run build                       # 构建生产版本

# Git
git add . && git commit -m "msg"    # 提交
git push origin master              # 推送

# 数据库
sqlite3 lab_orchestrator.db .dump   # 导出 SQLite 数据
```
