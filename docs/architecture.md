# Lab Orchestrator — 完整架构文档

> 最后更新: 2026-07-23
> 面向读者: 开发者、架构师、运维人员

---

## 目录

1. [系统全景图](#1-系统全景图)
2. [后端架构](#2-后端架构)
3. [前端架构](#3-前端架构)
4. [AI Agent 架构](#4-ai-agent-架构)
5. [数据模型与数据库](#5-数据模型与数据库)
6. [API 完整端点](#6-api-完整端点)
7. [数据流详解](#7-数据流详解)
8. [安全模型](#8-安全模型)
9. [部署架构](#9-部署架构)

---

## 1. 系统全景图

```
┌──────────────────────────────────────────────────────────────────┐
│                        用户浏览器 (Vue 3)                          │
│                                                                   │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────┐ │
│  │ 登录    │ │ 仪表盘  │ │ 板子   │ │ 预约   │ │ 实验   │ │AI   │ │
│  │ 注册    │ │ 统计   │ │ 管理   │ │ 系统   │ │ 控制台 │ │助手 │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └─────┘ │
│                                                                   │
│   Pinia 状态管理 ◄──► Axios HTTP ◄──► Vue Router (6页面)         │
└────────────────────────────┬──────────────────────────────────────┘
                             │  HTTP REST + JWT (Bearer Token)
                             │  CORS: localhost:5173
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FastAPI 后端 (:8000)                          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     API 路由层 (4模块)                        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │ │
│  │  │ auth.py  │ │boards.py │ │bookings  │ │experiments   │   │ │
│  │  │ 3端点    │ │ 5端点    │ │.py 3端点 │ │.py 6端点     │   │ │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘   │ │
│  └───────┼────────────┼────────────┼───────────────┼───────────┘ │
│          │            │            │               │              │
│  ┌───────┼────────────┼────────────┼───────────────┼───────────┐ │
│  │       ▼            ▼            ▼               ▼            │ │
│  │                  服务层 (Services)                            │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────────┐   │ │
│  │  │BoardManager│ │Scheduler   │ │ExperimentEngine        │   │ │
│  │  │ (连接池)    │ │(预约引擎)  │ │(实验执行引擎)          │   │ │
│  │  │            │ │            │ │                        │   │ │
│  │  │asyncssh    │ │冲突检测    │ │顺序执行步骤            │   │ │
│  │  │pyserial    │ │排他锁      │ │结果收集                │   │ │
│  │  │心跳检测    │ │超时释放    │ │状态流转                │   │ │
│  │  └─────┬──────┘ └────────────┘ └────────────────────────┘   │ │
│  └────────┼──────────────────────────────────────────────────────┘ │
│           │                                                       │
│  ┌────────┼──────────────────────────────────────────────────────┐ │
│  │        ▼         AI Agent 模块                                │ │
│  │  ┌──────────────────────────────────────────────────────┐     │ │
│  │  │ agent.py          — Anthropic SDK 调度器              │     │ │
│  │  │ tools.py          — 8个工具定义 (Tool Use Schema)     │     │ │
│  │  │ prompts.py        — 系统提示词 + 计划模板              │     │ │
│  │  └──────────────────────────────────────────────────────┘     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    数据层                                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │ │
│  │  │ User     │  │ Board    │  │ Booking  │  │Experiment│     │ │
│  │  │ Model    │  │ Model    │  │ Model    │  │ Model    │     │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │ │
│  │                      │                                       │ │
│  │              SQLAlchemy ORM (Async)                           │ │
│  │              SQLite (dev) / PostgreSQL (prod)                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬──────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
              ┌──────────┐    ┌──────────────┐
              │ SSH (22) │    │ Serial (USB) │
              │ asyncssh │    │ pyserial     │
              └─────┬────┘    └──────┬───────┘
                    │                │
                    ▼                ▼
┌──────────────────────────────────────────────────────────────────┐
│                        板子集群                                    │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │RPi (SSH) │ │Jetson    │ │ESP32     │ │STM32     │ ...        │
│  │Docker    │ │(SSH)     │ │(Serial)  │ │(Serial)  │            │
│  │实验容器  │ │Docker    │ │裸机固件  │ │裸机固件  │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
│                                                                   │
│  连接方式: 网线→交换机→服务器 / USB Hub→USB转串口→服务器         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. 后端架构

### 2.1 技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web框架 | FastAPI | >=0.110 | 异步REST API |
| ORM | SQLAlchemy 2.0 | >=2.0.30 | 异步数据库操作 |
| 认证 | python-jose (JWT) | >=3.3 | Token签发验证 |
| 密码 | bcrypt | >=4.0 | 密码哈希 |
| SSH | asyncssh | >=2.14 | SSH连接池 |
| 串口 | pyserial | >=3.5 | 串口通信 |
| AI SDK | anthropic | >=0.40 | Claude API调用 |
| HTTP | httpx | >=0.27 | HTTP客户端(测试) |

### 2.2 目录结构详解

```
backend/
├── app/
│   ├── main.py                    ← FastAPI 应用实例化
│   │   ├── lifespan()            → 启动时 init_db() + 关闭时 disconnect_all()
│   │   ├── CORS 中间件           → 允许 localhost:5173 跨域
│   │   └── 4个路由注册           → auth/boards/bookings/experiments
│   │
│   ├── config.py                  ← 配置管理 (pydantic-settings)
│   │   └── Settings 类           → 从 .env 读取全部配置
│   │
│   ├── api/                       ← 路由层 (薄层，只做请求/响应)
│   │   ├── auth.py               → /api/auth/*
│   │   │   ├── POST /register    → 注册，返回JWT
│   │   │   ├── POST /login       → 登录，返回JWT
│   │   │   └── GET /me           → 获取当前用户
│   │   │
│   │   ├── boards.py             → /api/boards/*
│   │   │   ├── GET /             → 列出所有板子
│   │   │   ├── POST /            → 新增板子
│   │   │   ├── GET /{id}         → 查看单板
│   │   │   ├── POST /{id}/check  → 状态检查
│   │   │   └── POST /{id}/exec   → 执行命令
│   │   │
│   │   ├── bookings.py           → /api/bookings/*
│   │   │   ├── GET /             → 我的预约列表
│   │   │   ├── POST /            → 创建预约
│   │   │   └── POST /{id}/cancel → 取消预约
│   │   │
│   │   └── experiments.py        → /api/experiments/*
│   │       ├── GET /             → 我的实验列表
│   │       ├── POST /            → 创建实验
│   │       ├── GET /{id}         → 查看实验详情
│   │       ├── POST /{id}/run    → 执行全部步骤
│   │       ├── POST /{id}/step/{n} → 执行单步
│   │       └── POST /ai-chat/{id}  → AI对话 (核心)
│   │
│   ├── models/                    ← 数据模型 (SQLAlchemy ORM)
│   │   ├── user.py               → User: id, username, role, ...
│   │   ├── board.py              → Board: 连接信息, 状态, 锁
│   │   ├── experiment.py         → Experiment: 步骤JSON, 结果
│   │   └── booking.py            → Booking: 预约时间, 状态
│   │
│   ├── services/                  ← 业务逻辑层 (厚层)
│   │   ├── board_manager.py       → BoardConnection + BoardManager
│   │   │   ├── BoardConnection    -> 单板连接封装 (SSH/Serial)
│   │   │   │   ├── connect()      -> 建立连接
│   │   │   │   ├── disconnect()   -> 断开连接
│   │   │   │   ├── exec()         -> SSH执行命令
│   │   │   │   └── write_serial() -> 串口写入
│   │   │   └── BoardManager       -> 全局连接池 (asyncio.Lock)
│   │   │       ├── get_or_create() → 获取/新建连接
│   │   │       ├── exec_on_board() → 执行命令
│   │   │       └── check_health()  → 状态检测
│   │   │
│   │   ├── scheduler.py           → Scheduler 预约调度
│   │   │   ├── is_board_available()  → 时间冲突检查
│   │   │   ├── create_booking()      → 创建预约
│   │   │   └── cancel_booking()      → 取消预约
│   │   │
│   │   └── experiment_engine.py   → ExperimentEngine 执行器
│   │       ├── run_step()         → 执行单个步骤
│   │       └── run_all()          → 顺序执行全部步骤
│   │
│   ├── ai_agent/                  ← AI Agent (Anthropic)
│   │   ├── agent.py               → AIAgent 单例
│   │   │   ├── chat()             → 对话入口 (含Tool Use循环)
│   │   │   ├── _execute_tool()    → 工具调用分发
│   │   │   └── register_tool()    → 动态注册工具
│   │   │
│   │   ├── tools.py               → 工具定义 (Anthropic Schema)
│   │   │   ├── exec_command       → 执行shell命令
│   │   │   ├── run_experiment_step→ 执行实验步骤
│   │   │   ├── flash_firmware     → 烧录固件 (高危)
│   │   │   ├── compile_source     → 编译源码
│   │   │   ├── check_board_status → 检查板子状态
│   │   │   ├── list_boards        → 列出所有板子
│   │   │   ├── create_experiment_plan → 创建实验计划
│   │   │   └── read_log           → 读取日志
│   │   │
│   │   └── prompts.py             → 系统提示词
│   │       ├── SYSTEM_PROMPT      → AI角色+安全约束
│   │       └── PLAN_TEMPLATE      → 实验计划展示模板
│   │
│   └── db/
│       └── database.py            ← 数据库引擎
│           ├── engine             → SQLite async引擎
│           ├── init_db()          → 自动建表
│           └── get_db()           → 依赖注入获取session
│
├── .env                           ← 环境变量 (不提交git)
├── requirements.txt               ← Python依赖
└── Dockerfile                     ← 容器化部署
```

### 2.3 依赖注入链

```
API端点 → Depends(get_current_user) → Depends(get_db) → 业务逻辑
              │                            │
              └─ 从 Authorization header   └─ async_session_factory
                 解析JWT → 查用户表            生成 AsyncSession
```

### 2.4 异步执行模型

```
FastAPI (asyncio event loop)
  │
  ├── 并发请求处理 (非阻塞)
  │
  ├── BoardManager._lock (asyncio.Lock)
  │   └── 同一板子操作互斥, 不同板子并行
  │
  └── asyncssh / pyserial
      └── SSH连接池复用, 串口独占访问
```

---

## 3. 前端架构

### 3.1 技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 (Composition API) | >=3.4 | SPA |
| 语言 | TypeScript | >=5.4 | 类型安全 |
| 构建 | Vite | >=5.2 | 开发/打包 |
| 路由 | Vue Router 4 | >=4.3 | 页面路由 |
| 状态 | Pinia | >=2.1 | 全局状态 |
| HTTP | Axios | >=1.7 | API调用 |

### 3.2 组件树

```
App.vue
├── Navbar (header)
│   ├── Logo + 导航链接 (6个)
│   └── 用户名 + 退出按钮
│
├── <router-view/> ──── 根据路由渲染以下页面之一:
│
│   ├── Login.vue              ← /login
│   │   └── 注册/登录表单
│   │
│   ├── Dashboard.vue          ← /dashboard
│   │   ├── StatsGrid          → 4个统计卡片(板子/在线/实验/预约)
│   │   └── QuickLinks         → 4个快速入口
│   │
│   ├── Boards.vue             ← /boards
│   │   ├── AddForm            → 添加板子表单(SSH/Serial切换)
│   │   ├── BoardCard[]        → 板子列表卡片
│   │   │   ├── StatusBadge    → 在线/离线/占用/异常
│   │   │   ├── ActionButtons  → 检查/执行命令
│   │   │   └── ExecPanel      → 命令输入+输出显示
│   │   └──
│   │
│   ├── Booking.vue            ← /bookings
│   │   ├── BookingForm        → 新建预约(选择板子+时间)
│   │   └── BookingItem[]      → 预约列表(状态流转)
│   │
│   ├── Experiments.vue        ← /experiments
│   │   ├── ExpForm            → 创建实验表单
│   │   ├── ExpItem[]          → 实验列表(状态+运行按钮)
│   │   └── DetailModal        → 实验详情弹窗(步骤+输出)
│   │
│   ├── AIAgent.vue            ← /ai-agent ⭐
│   │   ├── BoardSelector      → 选择操作板子
│   │   ├── ChatMessages       → 对话历史
│   │   ├── ChatInput          → 输入框+发送
│   │   └── InfoPanel          → 使用说明
│   │
│   └── UserManual.vue         ← /manual
│       ├── TocSidebar         → 6个章节目录
│       └── ContentPanel       → 手册正文
│
└── Modal (全局) ← 实验详情/确认弹窗
```

### 3.3 状态管理

```
Pinia Store: useUserStore
├── token          ← JWT字符串 (localStorage持久化)
├── userInfo       ← {id, username, display_name, role}
├── isLoggedIn     ← computed: !!token
├── isAdmin        ← computed: role === 'admin'
├── login()        → POST /api/auth/login → 更新状态
├── register()     → POST /api/auth/register → 更新状态
└── logout()       → 清空状态 → 跳转/login
```

### 3.4 路由守卫

```
router.beforeEach(to, from):
  if to.meta.requiresAuth && !localStorage.token:
    → redirect /login
```

### 3.5 API 客户端 (Axios)

```
axios instance (baseURL: /api)
├── request interceptor      → 自动附加 Authorization: Bearer <token>
├── response interceptor     → 401时清空token并跳转/login
├── 30s 超时
└── Vite proxy: /api → http://localhost:8000 (开发环境)
```

---

## 4. AI Agent 架构

### 4.1 核心流程

```
用户在AI聊天页面输入自然语言
         │
         ▼
POST /api/experiments/ai-chat/{board_id}
         │
         ▼
AIAgent.chat(session_id, user_message)
         │
         ├── 1. 构建 messages = [system_prompt, ...history, user_message]
         │
         ├── 2. 调用 Anthropic Messages API
         │       ├── model: claude-sonnet-4-20250514
         │       ├── tools: 8个工具定义
         │       └── system: 安全约束提示词
         │
         ├── 3. 解析响应
         │       ├── text block      → 文本回复 (直接返回)
         │       └── tool_use block  → 执行工具调用
         │
         ├── 4. 执行工具
         │       └── _execute_tool(name, params)
         │           └── 分发到已注册的 handler 函数
         │               ├── exec_command        → BoardManager.exec_on_board()
         │               ├── list_boards         → DB查询
         │               ├── check_board_status  → BoardManager.check_health()
         │               ├── create_experiment_plan → DB插入
         │               ├── compile_source      → 编译命令
         │               ├── flash_firmware      → 高危操作阻止
         │               ├── read_log            → cat 文件内容
         │               └── run_experiment_step → ExperimentEngine.run_step()
         │
         └── 5. 返回回复给前端
```

### 4.2 安全三层防护

```
第1层: 工具约束
  AI不能自由编写shell命令
  → 只能调用预定义的8个工具函数
  → 每个工具的参数都有JSON Schema校验

第2层: 代码层禁止
  高危操作在handler中直接阻止
  → flash_firmware: 返回"需要用户二次确认"而不是执行
  → 后续可扩展: 白名单命令过滤

第3层: 人工确认
  涉及高危的实验计划
  → AI输出步骤计划
  → 用户手动点击"确认执行"
  → 才开始执行
```

### 4.3 对话会话管理

```
_conversations: dict[str, list[dict]]
  session_id = f"user_{user_id}_board_{board_id}"
  → 每个用户+板子组合独立会话
  → 历史消息保留在内存中
  → clear_conversation() 清空会话
```

### 4.4 Agent Core (独立层)

```
agent-core/ (与后端解耦, 可独立使用)

agent_core.py:
├── ExperimentStep      → 实验步骤数据类
├── ExperimentPlan      → 实验计划数据类
├── ExperimentValidator → 安全校验器
│   ├── DANGEROUS_ACTIONS → 高危动作关键词
│   └── validate()       → 返回警告列表
└── ExecutionResult     → 执行结果数据类

experiment_planner.py:
├── gpio_basic_test()      → GPIO输出测试模板
├── cpu_stress_test()      → CPU压力测试模板
├── memory_test()          → 内存读写测试模板
├── network_benchmark()    → 网络性能测试模板
├── firmware_flash_template() → 固件烧录模板 (高危)
└── EXPERIMENT_TEMPLATES   → 模板注册表
```

---

## 5. 数据模型与数据库

### 5.1 ER 图

```
┌──────────┐       ┌──────────────┐       ┌──────────┐
│  User    │       │   Booking    │       │  Board   │
├──────────┤       ├──────────────┤       ├──────────┤
│ id (PK)  │──1:N──│ user_id (FK) │       │ id (PK)  │
│ username │       │ board_id(FK) │──N:1──│ name     │
│ password │       │ start_time   │       │ type     │
│ role     │       │ end_time     │       │ status   │
│ email    │       │ status       │       │ conn_type│
│ created  │       │ title        │       │ host     │
└──────────┘       └──────────────┘       │ port     │
       │                                  │ serial   │
       │ 1:N                              │ locked   │
       ▼                                  └──────────┘
┌──────────────┐                               │
│ Experiment   │                               │ 1:N
├──────────────┤                               ▼
│ id (PK)      │                         ┌──────────┐
│ user_id (FK) │                         │ (板子被  │
│ board_id(FK) │                         │  预约    │
│ name         │                         │  占用)   │
│ steps (JSON) │                         └──────────┘
│ status       │
│ result       │
│ is_ai_driven │
│ log          │
└──────────────┘
```

### 5.2 表结构

**users**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| username | VARCHAR(50) UNIQUE | 登录名 |
| hashed_password | VARCHAR(255) | bcrypt哈希 |
| display_name | VARCHAR(100) | 显示名 |
| email | VARCHAR(100) UNIQUE | 邮箱(可选) |
| role | VARCHAR(20) | admin/user/viewer |
| is_active | BOOLEAN | 是否启用 |
| created_at | DATETIME | 注册时间 |
| last_login | DATETIME | 最后登录 |

**boards**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| name | VARCHAR(100) | 板子名称 |
| board_type | VARCHAR(20) | linux/mcu |
| status | VARCHAR(20) | online/offline/busy/error |
| conn_type | VARCHAR(20) | ssh/serial |
| host | VARCHAR(255) | SSH IP |
| port | INTEGER | SSH端口(默认22) |
| username | VARCHAR(100) | SSH用户名 |
| serial_port | VARCHAR(100) | 串口路径 |
| serial_baud | INTEGER | 波特率(默认115200) |
| locked_by | INTEGER | 占用者user_id |
| locked_at | DATETIME | 占用时间 |
| last_heartbeat | DATETIME | 最后心跳 |

**experiments**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| user_id | INTEGER FK | 创建者 |
| board_id | INTEGER FK | 目标板子 |
| name | VARCHAR(200) | 实验名称 |
| description | TEXT | 描述 |
| steps | TEXT (JSON) | 步骤数组 |
| status | VARCHAR(20) | pending→running→completed/failed |
| result_summary | TEXT | 结果摘要 |
| result_data | TEXT (JSON) | 结果数据 |
| is_ai_driven | INTEGER | 是否AI创建 |
| log | TEXT | 执行日志 |

**bookings**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 |
| user_id | INTEGER FK | 预约者 |
| board_id | INTEGER FK | 板子 |
| title | VARCHAR(200) | 预约标题 |
| start_time | DATETIME | 开始 |
| end_time | DATETIME | 结束 |
| status | VARCHAR(20) | pending→active→completed/cancelled |

### 5.3 数据库选型

| | SQLite (当前) | PostgreSQL (生产) |
|---|---|---|
| 场景 | 开发/演示 | 多人使用 |
| 并发 | 单写入者 | 高并发读写 |
| 部署 | 零配置 | 需要PG服务 |
| 迁移 | 直接替换连接字符串 |

```bash
# 切换到 PostgreSQL
# .env 中修改:
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/lab_orchestrator
```

---

## 6. API 完整端点

### 6.1 认证 (/api/auth)

| 方法 | 路径 | Auth | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | /register | 无 | `{username, password, display_name?}` | `{access_token, user_id, username, role}` |
| POST | /login | 无 | `{username, password}` | `{access_token, user_id, username, role}` |
| GET | /me | Bearer | — | `{id, username, display_name, role, is_active}` |

### 6.2 板子 (/api/boards)

| 方法 | 路径 | Auth | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | / | Bearer | — | `Board[]` (列表) |
| POST | / | Bearer | 见 BoardCreate schema | `Board` |
| GET | /{id} | Bearer | — | `Board` |
| POST | /{id}/check | Bearer | — | `{board_id, status}` |
| POST | /{id}/exec | Bearer | `{command, password?}` | `{output}` |

### 6.3 预约 (/api/bookings)

| 方法 | 路径 | Auth | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | / | Bearer | — | `Booking[]` |
| POST | / | Bearer | `{board_id, title?, start_time, end_time}` | `{success, booking_id?}` |
| POST | /{id}/cancel | Bearer | — | `{success}` |

### 6.4 实验 (/api/experiments)

| 方法 | 路径 | Auth | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | / | Bearer | — | `Experiment[]` |
| POST | / | Bearer | `{board_id, name, description?, steps?, is_ai_driven?}` | `Experiment` |
| GET | /{id} | Bearer | — | `Experiment` |
| POST | /{id}/run | Bearer | — | `{results}` |
| POST | /{id}/step/{n} | Bearer | — | `{success, step, output}` |
| POST | /ai-chat/{bid} | Bearer | `{message}` | `{reply}` ⭐ |

### 6.5 健康检查

| 方法 | 路径 | Auth | 响应 |
|------|------|------|------|
| GET | /api/health | 无 | `{status, app}` |

---

## 7. 数据流详解

### 7.1 用户注册登录

```
注册:
  前端 Login.vue → POST /api/auth/register
    → auth.py:register()
      → 检查用户名唯一性
      → bcrypt.hashpw(password)
      → User 插入 DB
      → jwt.encode(user_id, username, role)
      → 返回 token
    → 前端 store 保存 token + userInfo → localStorage
    → router.push('/dashboard')

登录:
  同上, 调用 POST /api/auth/login
    → bcrypt.checkpw(password, hashed)
    → 更新 last_login
    → 返回 token
```

### 7.2 手动操作板子

```
Boards.vue:
  [添加板子] → POST /api/boards/ → DB INSERT → 刷新列表
  [检查状态] → POST /api/boards/{id}/check
    → BoardManager.check_health()
      → SSH connect()
      → 返回 online/offline
    → 更新 DB status + last_heartbeat
  [执行命令] → POST /api/boards/{id}/exec
    → 检查 locked_by (排他控制)
    → BoardManager.exec_on_board()
      → BoardConnection.exec(command)
        → asyncssh.run(command)
    → 返回 output
```

### 7.3 预约流程

```
Booking.vue:
  [新建预约] → POST /api/bookings/
    → Scheduler.is_board_available()
      → 查询 Booking 表: 同时间段是否有冲突
    → 无冲突: INSERT Booking (status=pending)
    → 返回 booking_id

  时间到达 start_time 时:
    → activate_booking() → status=active
    → 用户在时间段内操作板子

  时间到达 end_time 时:
    → complete_booking() → status=completed
    → 板子释放
```

### 7.4 AI 辅助实验 (核心流程)

```
AIAgent.vue:
  用户输入: "帮我跑GPIO测试"
    → POST /api/experiments/ai-chat/{board_id}
    → AIAgent.chat(session_id, message)
      → Anthropic API Messages.create()
        → Claude 分析意图
        → 调用 create_experiment_plan(board_id, name, steps)
          → DB INSERT Experiment (status=pending, is_ai_driven=1)
        → 返回: "已创建实验计划，包含5个步骤，确认后执行"

  用户输入: "确认执行"
    → AIAgent.chat(session_id, "确认执行")
      → Claude 调用 run_experiment_step(exp_id, 0)
        → ExperimentEngine.run_step()
          → BoardManager.exec_on_board("gpio export 18 out")
          → 返回结果
      → Claude 调用 run_experiment_step(exp_id, 1)
        → BoardManager.exec_on_board("gpio write 18 1")
      → ...依次执行所有步骤
      → 返回: "实验完成，GPIO 18 输出正常"
```

---

## 8. 安全模型

### 8.1 认证层

```
请求到达
  → HTTPBearer 提取 Authorization header
  → jwt.decode(token, SECRET_KEY)
  → 从 DB 获取 User 对象
  → 检查 is_active
  → 注入到路由函数
```

### 8.2 授权层

| 操作 | 权限要求 |
|------|---------|
| 查看板子列表 | 已登录 |
| 添加板子 | 已登录 |
| 执行命令 | 已登录 + 板子未被占用 OR 自己是占用者 |
| 创建预约 | 已登录 |
| 取消预约 | 预约创建者 |
| 操作AI Agent | 已登录 |

### 8.3 排他控制

```python
# board_manager.py - exec_on_board
if board.locked_by and board.locked_by != user.id:
    raise HTTPException(403, "板子已被其他用户占用")
```

### 8.4 AI 安全

```
AI 不能做的:
  ✗ 自由编写 SSH 命令
  ✗ 直接烧录固件
  ✗ 访问其他用户的板子
  ✗ 删除系统文件

AI 可以做但需要确认的:
  △ 创建实验计划 → 用户确认后执行
  △ 执行编译脚本 → 限制在指定目录

AI 可以自由做的:
  ✓ 查询板子列表
  ✓ 检查板子状态
  ✓ 读取日志文件
```

---

## 9. 部署架构

### 9.1 开发环境 (当前)

```
笔记本电脑 (Windows 11 + WSL2/Git Bash)
├── 终端1: uvicorn app.main:app --reload --port 8000
├── 终端2: npm run dev --port 5173
└── Docker Registry (可选, 存实验镜像)
```

### 9.2 Phase 2: 生产环境

```
┌──────────────┐
│  Nginx       │ ← 反向代理 (443 HTTPS)
│  :443        │   静态文件 (frontend/dist/)
└──────┬───────┘
       │
       ├── /api/* → uvicorn (4 workers) :8000
       └── /*     → 静态文件
       
┌──────────────┐
│  FastAPI ×4  │ ← Gunicorn + Uvicorn Workers
│  :8000       │
└──────┬───────┘
       │
┌──────┴───────┐
│  PostgreSQL  │ ← 主数据库
│  Redis       │ ← 缓存 + 会话
└──────────────┘
```

### 9.3 Docker 部署

```bash
# 后端
cd backend
docker build -t lab-orchestrator-backend .
docker run -p 8000:8000 --env-file .env lab-orchestrator-backend

# 前端
cd frontend
npm run build
# dist/ 目录部署到 Nginx 或 CDN
```

## 10. 远程板子架构（board-agent 模式）

### 10.1 本地 vs 远程对比

```
本地板子:  服务器 ──主动SSH/串口──→ 板子  (板子和服务器同局域网)
远程板子:  服务器 ←──被动WebSocket── 板子 (板子主动"报到"服务器)
```

### 10.2 远程板子连接流程

```
1. 管理员在 Web 界面添加板子 → 选择"远程代理" → 生成 board_token
2. 在远程板子上启动 board-agent:
   python agent.py --server ws://服务器IP:8000/ws/board --token BOARD_TOKEN
3. board-agent 连接服务器 WebSocket → 发送注册消息 → 服务器验证 token
4. 板子状态变为 "online" → 用户可以向板子发送命令
5. 服务器通过 WebSocket 下发命令 → board-agent 本地执行 → 返回结果
```

### 10.3 消息协议

```
板子 → 服务器:
  { type: "register",      board_info: {...} }     // 注册
  { type: "heartbeat_ack", info: {...} }            // 心跳应答
  { type: "result",        cmd_id: "...", output: "..." }  // 命令结果

服务器 → 板子:
  { type: "registered",    board_id: 5 }            // 注册确认
  { type: "execute",       cmd_id: "...", command: "ls", timeout: 60 }
  { type: "heartbeat" }                              // 心跳检测
  { type: "shutdown" }                               // 关闭代理
```

### 10.4 部署 board-agent

```bash
# 在远程板子(Raspberry Pi/Jetson等)上:
git clone https://github.com/cringe-sigma/Lab-Orchestrator.git
cd Lab-Orchestrator/board-agent
pip install websockets

# 启动代理
python agent.py --server ws://你的服务器IP:8000/ws/board --token 系统生成的TOKEN

# 使用 systemd 保持运行:
# 见 board-agent/lab-agent.service
```
