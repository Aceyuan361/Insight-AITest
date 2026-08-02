# 项目架构概览

## Insight-AITest v2.1.0

**Insight-AITest** 是一款 AI 驱动的模块化测试与监控平台。平台内核（kernel）在启动时扫描各模块的 `manifest.yaml`，完成校验、拓扑排序并注册 FastAPI 路由与 WebSocket；React 外壳前端（shell）根据模块映射表渲染每个模块的界面。

- **后端**：Python 3.10+ · FastAPI · Uvicorn · SQLAlchemy 2.0 + SQLite · sqlite-vec（向量检索）
- **前端**：React 19 · TypeScript · Vite 7 · TailwindCSS · Zustand · ECharts · i18next
- **AI**：OpenAI 兼容协议（chat / embedding / vision），支持本地知识库（RAG）
- **设备**：Android（ADB）、iOS（pymobiledevice3）

## 项目结构

```
insight_aitest/
├── __main__.py              # 入口点：python -m insight_aitest（启动后端 + 前端 + 开浏览器）
├── platform/                # 平台内核（与具体功能无关的公共底座）
│   ├── kernel.py            # 装配 FastAPI 应用：config → db → 扫描模块 → 注册路由
│   ├── module_registry.py   # 模块清单解析、校验、拓扑排序
│   ├── api/                 # 平台级路由（健康检查、模块元数据等）
│   ├── persistence/         # 统一 SQLAlchemy engine/session 工厂、DB 迁移
│   └── services/            # 共享服务
│       ├── llm/             # LLM 客户端、配置、思考级别参数解析
│       ├── kb/              # 知识库向量存储、文档解析
│       ├── collectors/      # 性能指标采集器（Android / iOS）
│       ├── device_adapters/ # 设备适配器层（ADB / pymobiledevice3）
│       └── models/          # 共享数据模型
├── modules/                 # 可插拔功能模块（每个模块自带 manifest.yaml）
│   ├── ai/                  # C：测试 Agent（RAG 问答 + 计划→确认→执行）
│   ├── kb/                  # 知识库管理（文档上传、向量化）
│   ├── testcase/            # D：测试用例生成（场景分析 → 用例结构化）
│   ├── api/                 # E：API 自动化（多步骤用例、断言、环境、套件）
│   ├── ui/                  # F：UI 自动化（Midscene 视觉 + Playwright）
│   ├── performance/         # B：性能监控（实时指标 WebSocket、告警规则）
│   └── _registry/           # 模块可选基类（降低样板代码）
└── shell-frontend/          # React 外壳前端（独立 Vite 工程）
    ├── src/
    │   ├── modules/         # 与后端模块一一对应的前端模块
    │   ├── shared/          # 共享组件、i18n、hooks、store
    │   └── shell/           # 应用外壳（TopBar、SideNav、Dashboard、路由）
    ├── package.json
    └── vite.config.ts       # 端口 80，/api 代理到后端 8001
```

## 系统架构

```
                ┌──────────────────────────────────────┐
                │            platform/kernel            │
                │  扫描 manifest → 拓扑排序 → 注册路由    │
                └──────────────────┬───────────────────┘
                                   │ 装配
     ┌─────────────────────────────┼─────────────────────────────┐
     │                             │                             │
     ▼                             ▼                             ▼
┌─────────┐                ┌──────────────┐               ┌────────────┐
│ 平台服务 │                │  功能模块     │               │ 外壳前端    │
│ (shared) │                │ (modules/*)  │               │ (React)    │
├─────────┤                ├──────────────┤               ├────────────┤
│ llm     │◀──共享──────────│ ai / kb      │◀── /api 代理 ──│ shell-     │
│ kb      │                │ testcase     │    (Vite :80)  │ frontend   │
│ collectors│               │ api / ui     │               │            │
│ device_  │                │ performance  │               │ 模块映射表  │
│ adapters │                │              │               │ module-map │
└─────────┘                └──────────────┘               └────────────┘
     │                             │
     ▼                             ▼
┌─────────────┐           ┌──────────────────┐
│ 外部依赖     │           │  数据持久化        │
│ ADB / iOS   │           │ SQLite (WAL)      │
│ OpenAI API  │           │ sqlite-vec (向量)  │
└─────────────┘           └──────────────────┘
```

## 启动流程

`python -m insight_aitest`（或 Windows 双击 `start.bat`）会：

1. 后台线程启动前端 Vite 开发服务器（端口 80，缺失 `node_modules` 时自动 `npm install`）。
2. 后台线程延迟 5 秒打开浏览器。
3. 主线程装配 FastAPI 应用并启动 Uvicorn（端口 8001）。
4. 前端通过 Vite 代理把 `/api/*`（含 WebSocket）转发到后端 8001。

| 服务      | 地址                        |
|-----------|----------------------------|
| 前端界面  | http://localhost:80        |
| 后端 API  | http://localhost:8001      |
| API 文档  | http://localhost:8001/docs |

## 模块体系

每个模块目录包含一个 `manifest.yaml`，声明模块的 `id`、`name`、`backend.router`（FastAPI 路由）、`frontend.entry`（React 入口组件）、`frontend.route`（前端路由路径）、导航项等。内核据此完成：

- **校验**：必填字段、路由冲突、依赖声明。
- **拓扑排序**：按 `dependencies` 解决模块间加载顺序。
- **注册**：挂载后端路由、WebSocket、前端导航项。

新增模块只需在 `modules/` 下创建目录并编写 `manifest.yaml`，无需改动内核——这是平台可扩展性的核心。

## 配置

AI 相关模块通过环境变量或配置文件提供 LLM 凭据（优先级：环境变量 > 配置文件 > 默认值）：

| 环境变量 | 说明 | 默认值 |
|---------|------|-------|
| `INSIGHT_EYE_AI_LLM_BASE_URL` | OpenAI 兼容 API 地址 | `https://api.openai.com/v1` |
| `INSIGHT_EYE_AI_LLM_API_KEY` | API 密钥 | （无，使用 AI 模块前必填） |
| `INSIGHT_EYE_AI_CHAT_MODEL` | 对话/推理模型 | `gpt-4o-mini` |
| `INSIGHT_EYE_AI_EMBED_MODEL` | 向量模型 | — |
| `INSIGHT_EYE_AI_VISION_MODEL` | 视觉模型（UI 自动化用） | 回退到对话模型 |

详见 `.env.example` 与 `config/ai.example.json`。运行时数据存放在 `~/.insight_eye/`（SQLite 库、向量索引、截图等，首次启动自动创建）。
