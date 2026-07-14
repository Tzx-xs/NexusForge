# Tech Context — NexusForge

## Tech Stack
- **语言**: Python 3.10+, TypeScript (前端)
- **后端框架**: FastAPI (异步)
- **数据库**: SQLite (WAL mode, PRAGMA foreign_keys=ON)
- **迁移工具**: Alembic
- **前端框架**: Vue 3.5+ (Composition API + `<script setup>`)
- **构建工具**: Vite 6+
- **状态管理**: Pinia
- **桌面框架**: Tauri 2
- **HTTP 客户端**: httpx (后端), fetch + EventSource (前端)
- **LLM**: OpenAI-compatible API (OpenAI / Anthropic / Ollama)
- **向量存储**: ChromaDB (可选) / SimpleVectorStore (n-gram fallback)
- **Token 计数**: tiktoken (可选) / 中英文比例估算
- **加密**: cryptography (AES-GCM, 可选)
- **YAML**: PyYAML (可选, 有简易 fallback)

## Project Structure
```
nexus-local/
├── .vibe/memory-bank/          # Memory Bank (vibe-tools)
├── .vibe/vibe.json             # vibe-tools 配置
├── .vibe/tools.json            # 工具定义
├── .vibe/workflows.json        # 工作流定义
├── backend/
│   ├── main.py                 # FastAPI 入口 (lifespan)
│   ├── alembic/                # Alembic 数据库迁移
│   ├── alembic.ini             # Alembic 配置
│   ├── config/                 # 配置模块
│   │   ├── settings.py         # Settings (pydantic-settings)
│   │   ├── defaults.py         # 默认常量
│   │   └── logging.py          # 日志配置
│   ├── domain/                 # 领域层 (纯 Python, 无框架依赖)
│   │   ├── shared/             # 共享值对象 + 异常
│   │   ├── novel.py, chapter.py, character.py, ...
│   │   ├── memory/             # FactLock, BeatLock, ClueLock
│   │   ├── knowledge/          # KnowledgeTriple, ChapterSummary
│   │   ├── structure/          # Storyline, StorylineNode
│   │   └── evolution/          # Snapshot
│   ├── application/            # 应用层 (服务编排)
│   │   ├── llm_client.py       # get_llm_client() 单例工厂
│   │   ├── agent/              # AgentService (Function Calling)
│   │   ├── voice/              # VoiceService + VoiceAnalyzer + VoiceModels
│   │   └── ...
│   ├── engine/                 # 引擎层 (自主写作)
│   │   ├── autonomous_engine.py  # AutonomousWritingEngine
│   │   ├── pipeline/           # Pipeline + Steps + Aftermath
│   │   │   ├── pipeline.py     # Pipeline (主管线)
│   │   │   ├── steps.py        # 7 个主步骤
│   │   │   ├── aftermath.py    # 旧版章后管线 (5次LLM)
│   │   │   └── unified_aftermath.py  # 新版统一章后管线 (1次LLM)
│   │   ├── runtime/            # 守护进程运行时
│   │   │   ├── daemon.py       # EngineDaemon
│   │   │   ├── circuit_breaker.py  # 熔断器
│   │   │   └── daemon_loop.py  # 守护进程主循环
│   │   ├── prompts/            # YAML 提示词模板
│   │   └── events/             # SSE 事件定义
│   └── infrastructure/         # 基础设施层
│       ├── ai/
│       │   ├── base_provider.py       # BaseProvider (ABC)
│       │   ├── providers/             # OpenAI/Anthropic/Ollama/Local
│       │   ├── llm_client.py          # LLMClient (重试/流式/JSON)
│       │   ├── provider_factory.py    # Provider 工厂
│       │   ├── prompt_manager.py      # PromptManager (YAML)
│       │   ├── prompt_registry.py     # PromptRegistry (可覆写节点)
│       │   ├── prompt_packages/       # StellarScribe + PlotPilot 提示词包
│       │   ├── embedding_service.py   # EmbeddingService
│       │   ├── vector_store.py        # BaseVectorStore (ABC)
│       │   └── chromadb_vector_store.py  # ChromaDB + SimpleVectorStore
│       ├── persistence/
│       │   ├── database.py            # Database (SQLite, Alembic)
│       │   ├── schema.sql             # DDL 参考文档
│       │   └── *_repo.py              # 各实体 Repository
│       ├── tools/                     # BaseTool + 实用工具
│       ├── crypto.py                  # AES-GCM 加密/解密
│       └── validators.py             # SSRF 防护
├── frontend/                   # PlotPilot UI (Vue 3 + Tauri 2)
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # 可复用组件
│   │   ├── stores/             # Pinia stores
│   │   ├── composables/        # 组合式函数
│   │   ├── api/                # 后端 API 封装
│   │   └── types/              # TypeScript 类型
│   ├── vite.config.ts
│   └── package.json
├── data/                       # 运行时数据
│   ├── novels.db               # SQLite 数据库
│   ├── vector_store.json       # SimpleVectorStore 数据
│   └── output/                 # 章节输出目录
└── prompts/                    # 旧版提示词 (已被 prompt_packages 替代)
```

## Key Configuration
- `Settings` (pydantic-settings): `LLM_PROVIDER`, `DEFAULT_MODEL`, `API_KEY`, `API_BASE_URL`
- `config/defaults.py`: 所有默认常量 (超时、重试次数、阈值等)
- API Key 存储: AES-GCM 加密 (cryptography 库)，开发模式机器派生密钥兜底
- SQLite WAL mode + busy_timeout=5000ms
