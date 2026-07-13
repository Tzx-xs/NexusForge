# 星渊笔（XingYuanBi）Code Wiki

> AI 长篇小说写作系统 · 全栈技术文档
> 版本基于代码仓库快照（2026-07-11）

---

## 目录

1. [项目概览](#1-项目概览)
2. [整体架构](#2-整体架构)
3. [主要模块职责](#3-主要模块职责)
4. [关键类与函数说明](#4-关键类与函数说明)
5. [依赖关系](#5-依赖关系)
6. [项目运行方式](#6-项目运行方式)
7. [盲审：可信性与欠缺点](#7-盲审可信性与欠缺点)

---

## 1. 项目概览

### 1.1 项目定位

**星渊笔**是一款面向网文作者的 AI 辅助长篇小说创作工作台，覆盖从灵感、大纲、章节写作、人物/世界观设定、质量审查到导出的完整创作链路。系统强调「叙事一致性」与「文风稳定」，通过长期记忆锁、知识图谱、向量检索 RAG、文风指纹漂移检测等机制保证 AI 生成内容的连贯性。

### 1.2 技术栈一览

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 + FastAPI + Uvicorn + Pydantic v2 + 原生 sqlite3 + Alembic |
| AI/向量 | OpenAI / Anthropic / Ollama 多 Provider + ChromaDB + sentence-transformers + tiktoken |
| 前端 | Vue 3.4 + TypeScript 5.4 + Vite 6 + Pinia 2 + Vue Router 4 + Naive UI + Tiptap |
| 桌面壳 | Tauri 1.5 (Rust 2021) |
| 部署 | Docker + Fly.io + EdgeOne Pages + 桌面安装包 |
| 工具链 | Ruff + mypy + pytest + ESLint + vue-tsc + Vitest + Bandit + pip-audit |

### 1.3 仓库布局

```
/workspace
├── backend/              # Python 后端（FastAPI）
│   ├── interfaces/       # API 路由、中间件、DI 容器、main.py
│   ├── application/      # 应用服务、审计护栏、生成管线、记忆、文风
│   ├── domain/           # 领域模型（纯数据/规则，无 IO）
│   ├── infrastructure/   # 持久化、AI Provider、向量库、工具
│   ├── agents/           # Agent 编排 + 工具集
│   ├── engine/           # 通用 Pipeline 基类
│   ├── config/           # settings / defaults / logging
│   ├── migrations/       # Alembic 增量迁移（001-007）
│   ├── tests/            # 单元 + 集成测试
│   └── alembic/          # Alembic 配置
├── frontend/             # Vue 3 前端
│   └── src/
│       ├── api/          # 17 个 API 模块 + http.ts + sseParser.ts
│       ├── stores/       # 13 个 Pinia store
│       ├── views/        # 页面
│       ├── components/   # 组件（workspace / common / outline / quality / voice）
│       ├── composables/  # useAiGenerate / useAutoSave 等
│       └── router/       # 路由表
├── src-tauri/            # Tauri 桌面壳（Rust）
├── scripts/              # 检查脚本 + 图标生成
├── .github/workflows/    # CI（4 个 job）
├── .trae/specs/          # Spec 驱动开发产物
├── Dockerfile / fly.toml / edgeone.json
└── start.py              # 桌面一键启动
```

---

## 2. 整体架构

### 2.1 分层架构（DDD / Clean Architecture）

后端采用清晰的四层分层，依赖方向：**interfaces → application → domain ← infrastructure**（依赖倒置）。

```
┌──────────────────────────────────────────────────────────────┐
│  interfaces/   API 路由 · 中间件 · DI 容器 · 异常处理         │
├──────────────────────────────────────────────────────────────┤
│  application/  服务编排 · 审计护栏 · 生成管线 · 记忆 · 文风   │
├──────────────────────────────────────────────────────────────┤
│  domain/       领域模型 · 状态机 · 共享基类/异常（零 IO）      │
├──────────────────────────────────────────────────────────────┤
│  infrastructure/  sqlite3 repos · LLM Provider · 向量库 · 工具│
└──────────────────────────────────────────────────────────────┘

       agents/  独立编排层（Agent + Planner + Tools）
       engine/  通用 Pipeline 基类（base/context/steps/recovery/aftermath）
```

**设计要点**：
- `domain` 层零 IO 依赖，纯数据 + 规则，便于单测。
- `infrastructure` 实现 `domain` 定义的抽象接口（依赖倒置）。
- `agents` 与 `engine` 是横切编排层，不归入四层之内。

### 2.2 运行时数据流

```
                    ┌─────────────────────────────┐
                    │      前端 (Vue 3 + Tiptap)   │
                    └──────────────┬──────────────┘
                                   │ HTTP / SSE  (X-API-Key)
                                   ▼
                    ┌─────────────────────────────┐
                    │   FastAPI (interfaces/main)  │
                    │  18 个 v1 router + 中间件链   │
                    └──────────────┬──────────────┘
                                   │ Depends(get_*_service)
                                   ▼
                    ┌─────────────────────────────┐
                    │     Container (单例 DI)      │
                    │  组装 repos / services / AI  │
                    └──────────────┬──────────────┘
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
       ┌──────────────┐  ┌────────────────┐  ┌──────────────┐
       │ WritingAgent │  │ GenerationPipe │  │ Autonomous   │
       │  + 10 Tools  │  │  (4 步 SSE)    │  │ Writer 状态机│
       └──────┬───────┘  └────────┬───────┘  └──────┬───────┘
              │                   │                 │
              └──────────┬────────┴─────────────────┘
                         ▼
            ┌────────────────────────────┐
            │   Application Services     │
            │ ChapterService / BibleSvc  │
            │ ReviewSvc / VoiceSvc / ... │
            └────────────┬───────────────┘
                         ▼
            ┌────────────────────────────┐
            │  ContextBuilder (T0~T3 洋葱)│
            │  + MemoryEngine (铁锁)      │
            │  + VectorStore (RAG)        │
            └────────────┬───────────────┘
                         ▼
            ┌────────────────────────────┐
            │  LLMClient → Provider       │
            │  (OpenAI / Anthropic /      │
            │   Ollama / Local mock)      │
            └────────────┬───────────────┘
                         ▼
            ┌────────────────────────────┐
            │  AftermathPipeline (6 步)   │
            │  summary/triples/foreshadow │
            │  /memory/vector/snapshot    │
            └────────────┬───────────────┘
                         ▼
            ┌────────────────────────────┐
            │  SQLite (WAL) + ChromaDB   │
            └────────────────────────────┘
```

### 2.3 双管线并存

| 管线 | 路径 | 触发方 | 模式 |
|---|---|---|---|
| **GenerationPipeline** | `application/engine/generation_pipeline.py` | 用户在前端点击「续写」 | SSE 流式，4 步（build_context → generate_content → run_review → save_finalize） |
| **StoryPipeline** | `engine/pipeline/base.py` | Agent 通过 `generate_chapter` 工具自动调用 | 批处理，10 步（含 AftermathPipeline 集成） |

两者共享 `AftermathPipeline`（6 步章后处理）完成知识沉淀，职责互补不可合并。

---

## 3. 主要模块职责

### 3.1 后端模块

#### 3.1.1 `interfaces/` — 接口层
- **`main.py`**：FastAPI 应用入口。lifespan 启动校验配置 + 初始化 DB + 默认设置；中间件链（CORS → API Key 认证 → 请求 ID → 安全头/CSP）；异常处理（DomainException → HTTP 状态码映射）；注册 18 个 v1 路由器；挂载 `frontend/dist` 静态文件。
- **`container.py`**：`Container` 单例 DI 容器。懒加载初始化 DB → 13 个 Repository → AI（LLM/Prompt/Embedding/Vector）→ Engine（ContextBuilder/MemoryEngine/Audit/Voice/Pipeline）→ Services + ToolRegistry + WritingAgent。支持 `reload_llm_from_db` 运行时热重载。
- **`dependencies.py`**：FastAPI `Depends` 入口，一组 `get_*()` 函数暴露容器内服务。
- **`api/v1/`**：18 个路由模块（novels/chapters/bible/review/review_tasks/settings/memory/knowledge/foreshadows/quality/voice/autonomous/agent/storylines/worldview/snapshots/export/search）。
- **`middleware/`**：`auth.py`（API Key 认证）、`rate_limit.py`（限流）。
- **`utils/`**：`response.py`（统一响应壳 `{code, message, data}`）、`sse_utils.py`（SSE 事件封装）。

#### 3.1.2 `application/` — 应用服务层
- **`services/`**：领域服务编排。`chapter_service.py`（章节 CRUD + 生成调度）、`novel_service.py`、`bible_service.py`（人物 + 世界设定）、`review_service.py`、`export_service.py`（txt/md/html/docx/epub）、`search_service.py`（跨 5 表全文搜索）、`worldview_service.py`、`settings_service.py`、`review_task_service.py`。
- **`audit/`**：质量审计护栏系统。`audit_service.py`（注册式 + `asyncio.gather` 并行执行）+ 8 个 Guard（anti_ai / character_consistency / language_style / rhythm / plot_density / macro_rhythm / pov / naming_consistency）。
- **`engine/`**：生成管线核心。
  - `generation_pipeline.py`：4 步 SSE 流式生成。
  - `autonomous_writer.py`：状态机驱动的自动驾驶写作引擎（IDLE→PLANNING→GENERATING→AUDITING→REWRITING→AFTERMATH→COMPLETED/FAILED/PAUSED）。
  - `context_builder.py`：四层洋葱上下文构建（T0 铁锁 / T1 圣经 / T2 近文+RAG / T3 当前章纲）。
  - `context_budget_allocator.py`：Token 预算分配。
  - `prompt_manager.py`：Prompt 模板加载。
  - `steps/`：4 个 Step 类（build_context / generate_content / run_review / save_finalize）。
- **`memory/`**：长期记忆系统。
  - `memory_engine.py`：构建 T0 Iron Lock（不可违背约束集合）。
  - `state_extractor.py`：LLM 抽取章节后状态（facts/summary/beats/clues/triples）。
  - `narrative_memory_service.py`：章后记忆编排。
- **`voice/`**：文风系统。`voice_extractor.py`（多维指纹提取）、`voice_drift_detector.py`（加权漂移检测）、`voice_rewriter.py`（针对性改写 prompt）、`voice_service.py`（编排入口）。

#### 3.1.3 `domain/` — 领域模型
- 核心实体：`Novel` / `Chapter` / `Character` / `Foreshadow` / `ReviewResult` / `WorldSetting` / `Conversation` / `Message` / `ReviewTask`。
- `chapter_status.py`：章节状态机（DRAFT → PLANNED → COMPLETED）。
- `evolution/snapshot.py`：Git-like 章节版本快照（>10KB gzip 压缩）。
- `knowledge/`：`ChapterSummary` + `KnowledgeTriple`（S-P-O 三元组）。
- `memory/`：三类锁 — `FactLock`（不可变事实）/ `BeatLock`（已完成节拍）/ `ClueLock`（待收伏笔）。
- `structure/`：`BeatSheet` + `Storyline` + `StorylineNode`（带画布坐标的 DAG）。
- `shared/`：`BaseEntity` 基类、`exceptions.py`、`error_codes.py`。

#### 3.1.4 `infrastructure/` — 基础设施层
- **`persistence/`**：原生 sqlite3 Repository（13 个）+ `schema.sql`（334 行，20+ 表）+ `database.py`（线程局部连接 + WAL 优化 + Alembic 迁移 + 降级方案）。
- **`ai/`**：
  - `base_provider.py` + `provider_factory.py` + 4 个 Provider（openai/anthropic/ollama/local），统一返回 OpenAI 兼容 tool_calls。
  - `llm_client.py`：高层封装（chat / chat_json / chat_with_tools / chat_stream + 重试退避）。
  - `embedding_service.py`：OpenAI 优先，降级 SimpleHashEmbedding。
  - `chromadb_vector_store.py`：ChromaDB + SimpleVectorStore 内存降级。
  - `prompts/`：YAML 模板（chapter-content / chapter-outline / content-review）。
- **`tools/`**：文本工具（format_validator / red_line_checker / score_calculator / text_cleaner / word_counter）。
- **`crypto.py`**：AES-GCM 加密（API Key 落库加密）。
- **`validators.py`**：输入校验。

#### 3.1.5 `agents/` — Agent 编排
- **`agent_engine.py`**：`WritingAgent` 主编排器。`chat()` 主循环 yield SSE 事件；防 prompt 注入；三级降级（原生 Function Calling → JSON prompt → 纯文本流式）；工具调用上限保护；并行/串行工具执行。
- **`planner.py`**：`TaskPlanner`（LLM 分解意图为有序步骤）+ `PlanValidator`（DFS 检测循环依赖）+ `PlanExecutor`（按依赖顺序执行 + 重试）。
- **`system_prompt.py`**：Agent 系统提示词（身份 + 8 步工作流 + 星渊叙事法 + 工具指引 + 安全约束）。
- **`memory_compressor.py`**：长对话历史压缩。
- **`tools/`**：10 个 Tool（generate_chapter / review_chapter / query_bible / query_characters / manage_foreshadows / export_novel / edit_paragraph / delete_character / polish_content / analyze_plot），通过 `ToolRegistry.create_default` 统一组装。

#### 3.1.6 `engine/pipeline/` — 通用管线基类
- `base.py`：`PipelineStep` 抽象 + `PipelineContext` + `StepResult`。
- `steps.py`：标准步骤实现。
- `recovery.py`：检查点保存/加载 + `can_resume`。
- `aftermath.py`：`AftermathPipeline`（6 步章后处理：ExtractSummary / ExtractTriples / UpdateForeshadowing / UpdateMemory / IndexVector / CreateSnapshot）。
- `context.py`：管线运行时上下文。

### 3.2 前端模块

#### 3.2.1 `api/` — 通信层
- **`http.ts`**：Axios 实例。`API_BASE_URL=/api/v1`；从 sessionStorage 读 `xy-api-key` 注入 `X-API-Key`；响应拦截器拆解 `{code, message, data}` 信封；401 自动重试一次。
- **`sseParser.ts`**：统一 SSE 解析器（`parseSseBlocks`），消除 4 处重复。
- **17 个 API 模块**：novels / chapters / agent / aiSuggest / bible / autonomous / quality / review / snapshots / storylines / foreshadows / memory / voice / knowledge / worldview / search / settings / export。流式接口用原生 `fetch` + `ReadableStream` reader（axios 不支持流消费），120 秒超时。

#### 3.2.2 `stores/` — Pinia 状态管理（13 个 Store）
全部 Composition API 风格。关键 store：
- `novel.ts`：小说列表/分页（60s 缓存 TTL）+ 并发拉取 stats。
- `chapter.ts`：章节列表与当前章节，带版本号防竞态。
- `agentPanel.ts` / `aiConsole.ts`：AI 面板可见性（替代 props 透传）。
- `theme.ts`：4 模式（light/dark/abyss/system），独立持久化。
- `saveStatus.ts` / `editorStatus.ts`：自动保存与光标位置状态。
- `search.ts`：全局搜索（5 类：characters/foreshadows/facts/settings/chapters）。

#### 3.2.3 `views/` — 页面
- `Dashboard.vue`：首页容器，异步切换 4 个模块。
- `Workspace.vue`：工作台外壳（3 插槽布局）。
- `WritingPage.vue`：写作页（EditorPanel + FileViewer）。
- `BiblePage.vue` / `CharactersPage.vue`：设定圣经 / 人物管理（含五维雷达图）。
- `ReviewPage.vue` / `OutlinePage.vue` / `Settings.vue` / `NewBookWizard.vue`。

#### 3.2.4 `components/workspace/` — 工作台组件
- `WorkspaceShell.vue`：三栏 grid 布局 + 顶栏 KPI + 全局搜索 + 模式切换 + 底部状态栏。
- `EditorPanel.vue`：Tiptap 富文本编辑器（工具栏 + 行号 + DOMPurify 消毒 + 4 个 composables 集成）。
- `AgentChatPanel.vue`：AI 对话面板（SSE 流式 + tool_call 可视化 + AbortController 取消）。
- `AiConsole.vue`：AI 控制台（generate/quality/voice/ironlock/foreshadow/history 多 tab）。
- `ChapterRail.vue` / `ContextPanel.vue` / `FileViewer.vue` / `ForeshadowPanel.vue` / `IronLockPanel.vue`。

#### 3.2.5 `composables/` — 组合式函数
- `useAiGenerate.ts`：AI 续写核心（fetch SSE + token 流式追加 + 120s 超时 + AbortController）。
- `useAutoSave.ts`：防抖自动保存（2000ms）。
- `useWordCount.ts`：字数统计（中文按字符 + 英文按单词，250ms 防抖）。
- `useEditorCommands.ts` / `useVisualLineCount.ts` / `useCurrentNovelId.ts`。

### 3.3 Tauri 桌面壳

- `src-tauri/src/main.rs`：极简 Rust 入口。`windows_subsystem = "windows"`；维护 `AppState { project_dir }`；3 个 `#[tauri::command]`：`get_app_version` / `set_project_dir` / `get_project_dir`。业务逻辑全在 Python 后端，Tauri 仅负责窗口与版本号。
- `tauri.conf.json`：`allowlist` 仅开放 `window.all`（最小权限）；CSP 白名单允许 OpenAI/Anthropic/Ollama 端点；窗口 1400×900。

---

## 4. 关键类与函数说明

### 4.1 后端核心类

#### `interfaces/container.py` — `Container`
- 单例（`get_instance()` 懒加载）。
- `__init__` 按序初始化：DB → Repos → Settings → AI → Engine → Services。
- `_build_llm_client`：优先从数据库读配置（解密 api_key），失败回退环境变量 — 实现 UI 改配置即时生效。
- `reload_llm_from_db`：配置更新后重建所有依赖 LLM 的对象，拆分为 `_reload_engine_components` / `_reload_application_services` / `_reload_agent_components` 三子方法。

#### `agents/agent_engine.py` — `WritingAgent`
- `chat()`（行 53-220）：主循环 yield `(event_type, data)` SSE 事件元组。
  - `_sanitize_user_message`（行 706-737）：防 prompt 注入，包裹 `<user_message>` XML 标签。
  - `_prepare_conversation`（行 226-263）：获取/创建会话并持久化用户消息。
  - `_create_or_update_plan`（行 295-321）：仅新会话创建计划。
  - 工具调用主循环：优先原生 Function Calling → 降级 JSON prompt → 再降级纯文本流式。
  - 工具调用上限 `DEFAULT_MAX_TOOL_CALLS`，超限报 E4005。
- `_execute_tool_with_lifecycle`（行 362-449）：统一 10 步生命周期（生成 tool_call_id → yield tool_call → requires_confirmation 检查 → validate_args → execute → yield tool_result → _explain_tool_result → 推进计划）。
- `_execute_parallel_tools`（行 529-681）：分类独立/依赖工具，独立工具 `asyncio.gather` 并行。

#### `agents/planner.py` — `TaskPlanner` / `PlanValidator` / `PlanExecutor`
- `TaskPlanner.create_plan`（行 87-135）：LLM 将自然语言意图分解为有序步骤 JSON。
- `PlanValidator`（行 238-304）：DFS 检测循环依赖、空步骤、缺失依赖、自引用。
- `PlanExecutor`（行 312-398）：按依赖顺序执行，支持重试（0.5s × attempt 退避）。

#### `application/engine/generation_pipeline.py` — `GenerationPipeline`
- `generate_content_stream`（行 255-353）：主入口。
  1. 获取章节 + `try_acquire_generation_lock` 防并发。
  2. Step1 构建上下文。
  3. Step2 流式生成（yield outline/token/content_complete，进度按字数/4000 估算）。
  4. Step3 审查（`skip_on_error=True`，仅 warning）。
  5. Step4 保存。
  6. Aftermath（异常不阻塞主流程）。
  7. `finally: _cleanup_status` 防内存泄漏（PERF-C1）。
- `_retry_step`（行 355-379）：通用重试，0.5s × (attempt+1) 退避。

#### `application/engine/autonomous_writer.py` — `AutonomousWriter`
- 状态机：`AutoWriteState`（IDLE→PLANNING→GENERATING→AUDITING→REWRITING→AFTERMATH→COMPLETED/FAILED/PAUSED）。
- `_generate_single_chapter`（行 284-339）：核心重写循环 — 生成 → 审计 → 若不通过且 `auto_rewrite_on_fail` 则注入反馈重写（BLOCK-02）→ Aftermath → 文风漂移检测。5 分钟超时。
- `_check_voice_drift`（行 423-453，M-25）：检测文风指纹漂移，超阈值生成 rewrite_prompt。

#### `application/audit/audit_service.py` — `QualityAuditService`
- `run_audit`（行 72-164）：`asyncio.gather` 并行执行所有护栏（M-08），护栏异常包装为失败 GuardResult 不影响其他护栏。
- 评分逻辑：加权平均分，`passed = overall_score >= 60.0 and critical_issues == 0`。
- `with_default_guards`（行 166-186）：注册 8 个默认护栏。

#### `application/memory/memory_engine.py` — `MemoryEngine`
- `build_t0_iron_lock`（行 25-60）：聚合 immutable fact_locks + up_to_chapter 的 beat_locks + planted/developing 状态的 clue_locks，返回 `{facts, beats, clues}` 三段。
- `get_character_whitelist` / `get_death_list`（行 140-154）：从 `character_status` 类型 fact_locks 派生。
- `check_consistency`（行 167-180）：校验新内容是否违背铁锁（已死角色出现等）。
- `generate_memory_prompt`（行 182-204）：生成「记忆锁定」prompt。

#### `infrastructure/ai/llm_client.py` — `LLMClient`
- `chat_json`（行 124-162）：JSON 模式调用 + `json_repair` 兜底 + 正则提取 + 重试。
- `chat_with_tools`（行 164-196）：原生 Function Calling，返回 `ToolCallResult`。
- `_retry_loop`（行 284-318）：区分超时/限流/5xx 三类异常，独立重试次数，指数退避（2^attempt）。

#### `infrastructure/persistence/chapter_repo.py` — `ChapterRepository`
- `try_acquire_generation_lock`（行 11-28）：用 SQL 原子 UPDATE 实现乐观锁防并发生成。

### 4.2 前端核心函数

#### `api/http.ts`
- Axios 实例 + 请求拦截器（注入 `X-API-Key`）+ 响应拦截器（拆解信封 + 401 重试 + 错误去重防抖）。

#### `composables/useAiGenerate.ts`
- fetch SSE `/chapters/{id}/generate-content`，处理 token/progress/complete/error 事件，追加 delta 到 Tiptap 文档末尾，120s 超时，AbortController 取消。

#### `stores/chapter.ts`
- 章节列表与当前章节管理，带 `fetchChapterVersion` 版本号防竞态，网络波动时保留旧数据（MNT-L1）。

---

## 5. 依赖关系

### 5.1 后端依赖（`backend/requirements.txt`）

| 类别 | 依赖 | 用途 |
|---|---|---|
| Web | fastapi≥0.115, uvicorn[standard], pydantic≥2.9, httpx | API 框架 |
| DB | alembic≥1.13, sqlalchemy≥2.0 | 仅 Alembic DDL 迁移，运行时原生 sqlite3 |
| AI/向量 | chromadb≥0.5, sentence-transformers, faiss-cpu, tiktoken≥0.7 | 向量检索 + Token 计数 |
| 文档导出 | python-docx, ebooklib | docx/epub 导出 |
| 安全 | cryptography | AES-GCM 加密 |

> 注释明确标注 M-06 修复提升 starlette/cryptography 等版本下限以规避 CVE。

### 5.2 前端依赖（`frontend/package.json`）

| 类别 | 依赖 |
|---|---|
| 框架 | vue@3.4, vue-router@4.4, pinia@2.1 |
| 构建 | vite@6.2, typescript@5.4, @vitejs/plugin-vue |
| UI | naive-ui@2.39, @vicons/tabler |
| 编辑器 | @tiptap/vue-3, @tiptap/starter-kit, @tiptap/extension-placeholder/text-align/underline, @tiptap/pm |
| HTTP/MD | axios@1.7, marked, dompurify |
| 部署 | @iga-pages/cli@1.0.9 |
| 测试 | vitest@4.1, @vue/test-utils@2.4, jsdom@29, playwright@1.61 |

### 5.3 模块间依赖

```
WritingAgent ──→ ToolRegistry ──→ 10 Tools ──→ ApplicationServices
                       │                              │
                       │                              └─→ ChapterService ──→ GenerationPipeline
                       │                                                    │
                       │                              ┌─────────────────────┴───────────────────┐
                       │                              │  Step1 ContextBuilder (T0/T1/T2/T3)     │
                       │                              │     T0 = MemoryEngine.build_t0_iron_lock │
                       │                              │     T2 = vector_store.search (RAG)       │
                       │                              │  Step2 LLM chat_stream                   │
                       │                              │  Step3 RedLineChecker + LLM review       │
                       │                              │  Step4 chapter_repo + review_repo        │
                       │                              └─────────────────────┬───────────────────┘
                       │                                                    │
                       │                                                    ▼
                       │                              AftermathPipeline (6 步异步)
                       │                                  ├─ summary/triples → knowledge_repo
                       │                                  ├─ foreshadowing/memory → memory_repo
                       │                                  ├─ index_vector → vector_store
                       │                                  └─ create_snapshot → snapshot_repo
                       │
                       └─→ LLMClient ──→ Provider (OpenAI/Anthropic/Ollama/Local)
```

### 5.4 外部服务依赖

| 服务 | 用途 | 必需性 |
|---|---|---|
| OpenAI / Anthropic API | LLM 生成 | 二选一（生产） |
| Ollama | 本地 LLM（推荐 qwen2.5:14b） | 可选（本地部署） |
| ChromaDB（远程） | 向量检索 | 可选（默认嵌入式或 SimpleVectorStore 降级） |
| SQLite | 持久化 | 必需（自带） |

---

## 6. 项目运行方式

### 6.1 环境准备

#### 后端环境变量（`backend/.env.example`）

```bash
APP_ENV=production                 # production / development
APP_HOST=127.0.0.1                 # 公网部署改 0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:1420,tauri://localhost
API_KEY=                           # 桌面自动生成，公网手动设强随机
ENCRYPTION_KEY=                    # AES-GCM 64 字符 hex，生产必填
DATABASE_URL=sqlite:///./data/xingyuanbi.db

# LLM 配置（4 选 1）
LLM_PROVIDER=openai                # openai / anthropic / ollama / local
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
LLM_TIMEOUT=120

# 生成配置
GENERATION_MAX_RETRIES=2
GENERATION_STREAMING=true
CONTENT_TARGET_WORDS=2000
```

生成 `ENCRYPTION_KEY`：
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 前端环境变量（`frontend/.env.example`）

```bash
VITE_API_BASE_URL=http://localhost:8000
```

### 6.2 启动方式

| 场景 | 命令 | 说明 |
|---|---|---|
| **桌面一键启动** | `python start.py` | 自动 uvicorn + 可选 vite dev + 自动开浏览器；生产必须显式设 `API_KEY` |
| **后端裸跑（开发）** | `cd backend && python -m uvicorn interfaces.main:app --host 127.0.0.1 --port 8000` | |
| **前端开发** | `cd frontend && npm install && npm run dev` | Vite dev server，5173 端口，代理 `/api` 到 8000 |
| **容器/生产** | `docker build -t xingyuanbi . && docker run -p 8000:8000 xingyuanbi` | 4 worker uvicorn，非 root 用户 |
| **Fly.io 部署** | `fly deploy` | 用 `fly.toml`，持久卷挂载 `/data` |
| **Tauri 桌面开发** | `cd src-tauri && tauri dev` | 自动拉起前端 dev server，后端需另行启动 |
| **Tauri 打包** | `cd src-tauri && tauri build` | 产出各平台安装包 |

### 6.3 测试

#### 后端测试
```bash
cd backend
pytest                              # 全部测试
pytest --cov --cov-fail-under=50    # 带覆盖率门槛（CI 要求 ≥50%）
python api_check.py                 # 运行时 API 健康检查（需服务运行）
python tests/integration/e2e_comprehensive.py     # 独立 e2e 脚本
python tests/integration/e2e_deep_business.py     # 深度业务链路 e2e
```

测试覆盖：Agent / WritingAgent / 生成管线 / Planner / 章节服务 / 质量审计 / 记忆 / 向量 / 导出 / 快照 / 搜索 / 工具校验 / LLM / 迁移链等约 30 个测试文件。

#### 前端测试
```bash
cd frontend
npm run test          # vitest run
npm run type-check    # vue-tsc --noEmit
npm run lint          # eslint
npm run build         # vite build
```

#### 统一检查脚本（Windows）
```powershell
scripts\check.ps1           # 后端：ruff format + ruff check + mypy + pytest + api_check
scripts\check_frontend.ps1  # 前端：prettier + eslint + vue-tsc + vitest
```

### 6.4 CI 流水线（`.github/workflows/ci.yml`）

4 个 job：

| Job | 内容 | 失败阈值 |
|---|---|---|
| `backend-lint-and-test` | ruff check + ruff format --check + mypy + pytest --cov | 覆盖率 ≥50%，mypy 0 错误 |
| `frontend-lint-and-test` | npm ci + eslint --max-warnings=80 + vitest + vue-tsc + vite build | vue-tsc 0 错误，ESLint warning ≤80 |
| `security-scan` | pip-audit --strict + bandit | continue-on-error |
| `docker-build` | docker build + 容器冒烟测试（curl /health） | 依赖前两个 job 通过 |

### 6.5 数据库迁移

```bash
cd backend
alembic upgrade head    # 升级到最新
alembic downgrade -1    # 回退一步
alembic history         # 查看迁移链
```

迁移链：`001_initial_schema` → 002 → 003 → 004(FTS5) → 005 → 006(review_tasks) → 007(FTS5 触发器修复)。

> 注：运行时 `Database.init_db()` 会自动执行 `alembic upgrade head`，失败降级到 `schema.sql`。

---

## 7. 盲审：可信性与欠缺点

### 7.1 可信性评估（优点）

#### 架构成熟度高
1. **严格 DDD 分层**：`domain` 层零 IO 依赖，纯数据 + 规则，mypy 严格模式通过；依赖方向清晰（interfaces → application → domain ← infrastructure，依赖倒置）。
2. **单例容器 DI**：轻量但完整，无第三方 DI 框架，支持运行时 LLM 配置热重载（`reload_llm_from_db`），拆分为三子方法保证单一职责。
3. **双管线职责清晰**：GenerationPipeline（用户交互 SSE）与 StoryPipeline（Agent 批处理）互补不重叠，共享 AftermathPipeline 完成知识沉淀。

#### 工程质量过硬
4. **类型安全**：mypy 渐进式严格（domain 严格，其他渐进），前端 vue-tsc 0 错误门槛。
5. **测试覆盖**：后端约 30 个测试文件覆盖核心模块，CI 覆盖率门槛 ≥50%；前端有 store/component/composable/view 多层测试。
6. **CI 完备**：4 个 job 覆盖 lint / type-check / test / security-scan / docker-build，含容器冒烟测试。
7. **代码规范**：Ruff（E/F/I/UP/B/C4/SIM/W 规则）+ ESLint + Prettier + pre-commit。

#### 安全意识强
8. **CSP 严格**：生产环境 `script-src 'self'`，connect-src 白名单仅含已知 LLM 端点。
9. **Prompt 注入防御**：`_sanitize_user_message` 检测危险组合 + 移除 JSON 标记 + XML 标签包裹。
10. **API Key 加密**：AES-GCM 加密落库，`ENCRYPTION_KEY` 生产必填。
11. **破坏性工具确认**：`delete_character` 软删除 + `requires_confirmation=True`；`SKIP_DESTRUCTIVE_TOOLS` 环境变量兜底。
12. **错误信息脱敏**：非 debug 模式隐藏内部细节，仅返回「服务器内部错误」。
13. **容器最小权限**：非 root 用户 `appuser`（UID 1000）。
14. **Tauri 最小权限**：`allowlist` 仅开放 `window.all`。

#### 业务设计精巧
15. **四层洋葱上下文**（T0 铁锁 / T1 圣经 / T2 近文+RAG / T3 当前章纲）是 prompt 工程主干。
16. **三类记忆锁**（Fact/Beat/Clue Lock）+ 知识三元组 + 章节摘要构成长期记忆，`check_consistency` 防生成内容违背已确立事实。
17. **8 护栏并行审计** + 自动重写反馈闭环（BLOCK-02）。
18. **文风系统**：多维指纹 + 加权漂移检测 + 针对性改写 prompt，独立横切。
19. **统一 LLM Provider 抽象**：4 厂商通过 OpenAI 兼容 tool_calls 格式互通，含三级降级（原生 FC → JSON prompt → 纯文本流式）。
20. **乐观锁防并发**：`try_acquire_generation_lock` 用 SQL 原子 UPDATE。
21. **Git-like 章节快照**：>10KB gzip 压缩，content_hash + parent_snapshot_id 链式版本。
22. **RAG 闭环**：T2 层注入历史相关片段，Aftermath 索引新章节。

#### 运维友好
23. **多部署路径**：Fly.io（容器化 + 持久卷）+ EdgeOne（Serverless）+ Tauri 桌面 + 本地一键启动。
24. **降级方案完备**：Alembic 失败降级 schema.sql；ChromaDB 失败降级 SimpleVectorStore；OpenAI embedding 失败降级 SimpleHashEmbedding；各 Provider 失败降级 local mock。
25. **健康检查**：Dockerfile HEALTHCHECK + Fly.io + EdgeOne 均配置 `/health`。
26. **自动化机器省电**：Fly.io `auto_stop_machines=true`。

### 7.2 欠缺点与风险

#### 架构层面
1. **双轨 DB 设计脆弱**：运行时用原生 sqlite3，DDL 迁移用 Alembic（SQLAlchemy），两套机制并存易产生漂移。`schema.sql` 与 Alembic 迁移需手动保持同步，长期维护成本高。建议统一为 SQLAlchemy ORM 或纯 Alembic。
2. **单例容器 DI 难测试**：`Container.get_instance()` 全局单例，服务间强耦合，单元测试需大量 mock。无接口抽象，替换实现困难。
3. **`agents/` 与 `engine/` 边界模糊**：两套编排层并存（WritingAgent + GenerationPipeline + StoryPipeline + AutonomousWriter），职责有重叠，新人理解成本高。

#### 可扩展性
4. **SQLite 单文件瓶颈**：生产环境单 SQLite 文件，虽有 WAL 优化，但高并发写入场景下 `busy_timeout` 仍是瓶颈。Dockerfile `--workers 4` 与 SQLite 单文件写入存在潜在冲突（多 worker 共享文件锁）。
5. **向量库嵌入式默认**：ChromaDB 默认嵌入式，多 worker 时 collection 不共享，需显式配置 `CHROMA_HOST/PORT` 走远程模式。
6. **无消息队列**：AftermathPipeline 6 步异步处理在进程内执行，长任务失败后无重试队列，依赖 `recovery.py` 检查点恢复，但跨进程恢复能力有限。

#### 代码质量
7. **`state_extractor.py` 部分 TODO**：`_extract_beats/_extract_clues/_extract_triples` 是占位返回空列表（行 46-56），实际生产实现挪到 AftermathPipeline，但旧代码未清理，易误导。
8. **Spec 未完成项**：`.trae/specs/ui-fix-plan/checklist.md` 有未勾选项：`单元测试全部通过` / `页面加载时间正常` / `图谱渲染无明显卡顿` / `浮动抽屉响应迅速` / `编辑器输入流畅` — 性能验证与单元测试未完成。
9. **根级 `vitest.config.ts` 疑似遗留**：根目录有 `vitest.config.ts`，但前端 `package.json` 在 `frontend/`，CI 在 `frontend/` 跑测试，根级配置可能无效或历史遗留。
10. **ESLint warning 阈值宽松**：CI 允许 `--max-warnings=80`，且 `continue-on-error`，意味着 lint 实际不阻塞 CI。

#### 安全风险
11. **API Key 单一认证**：仅 `X-API-Key` 静态密钥，无 JWT/OAuth/Rate Limit per user。`rate_limit.py` 存在但粒度未知，公网部署风险高。
12. **`local_provider.py` 生产风险**：开发兜底返回 mock 文本，若生产误配 `LLM_PROVIDER=local` 会静默返回假数据。
13. **CSP 允许 Ollama localhost**：CSP connect-src 允许 `http://localhost:11434`，桌面应用可接受，但 Web 部署下用户浏览器无法访问他人 localhost，配置冗余。
14. **`SKIP_DESTRUCTIVE_TOOLS` 环境变量兜底**：可全局跳过破坏性工具确认，若误设会绕过安全防线。

#### 测试与验证
15. **覆盖率门槛 50% 偏低**：对于一个声称成熟的项目，50% 覆盖率门槛偏低，关键路径（生成管线、Agent 决策）应有更高覆盖。
16. **e2e 测试非 pytest**：`e2e_comprehensive.py` / `e2e_deep_business.py` 是独立脚本（用 `requests`），不纳入 pytest，CI 不自动运行。
17. **前端无 E2E 自动化**：`playwright` 在 devDependencies 但未见 E2E 测试目录（仅 `tests/ui-test.py` Python 脚本）。
18. **`.trae/specs/` 中 Playwright 验证**：spec 提到用 Playwright 浏览器自动化验证，但未纳入 CI。

#### 文档与可维护性
19. **无 API 文档**：生产环境关闭 `/docs`/`/redoc`/`/openapi.json`，虽有安全考虑，但无独立的 API 参考文档，对接成本高。
20. **无架构文档**：仓库内无 ADR（架构决策记录），关键设计（如双管线、四层洋葱上下文）仅散落在代码注释中。
21. **`api_check.py` 16 模块检查脚本**：是事实上的 API 文档，但需服务运行才能验证，无法离线查阅。

#### 运维与可观测性
22. **无指标采集**：未见 Prometheus/OpenTelemetry 集成，仅有日志文件（`logs/server.log`），生产可观测性不足。
23. **无分布式追踪**：虽有 `X-Request-ID`，但无链路追踪系统对接。
24. **日志本地文件**：Docker 容器日志写文件非 stdout，不符合 12-factor app，日志收集需额外配置。
25. **无数据备份策略**：SQLite 单文件 + Fly.io 持久卷，但仓库内无备份脚本或文档。

#### 业务逻辑
26. **文风系统阈值硬编码**：`VoiceDriftDetector.DEFAULT_THRESHOLDS` 与权重硬编码，无法按作者/题材调参。
27. **护栏权重固定**：8 个护栏权重（2.0/2.0/2.0/1.5/1.5/1.5/1.0/0.5）硬编码，无法按小说类型调整。
28. **`AntiAIGuard` 规则中文向**：检测的元话语/陈词滥调列表偏中文网文，对英文或其他语言创作支持有限。
29. **Tauri 桌面壳功能极简**：仅 3 个命令（版本号 + 项目目录记忆），实际仍是 Web 应用包装，未利用 Tauri 原生能力（文件系统、对话框等被 allowlist 关闭）。

### 7.3 综合评价

**可信性：中上**。该项目展现出成熟的工程实践（分层架构、类型安全、CI/CD、安全意识、降级方案），代码组织清晰，业务设计精巧（四层洋葱上下文、三类记忆锁、8 护栏、文风漂移检测）。从代码注释中的修复标记（M-01~M-25、BLOCK-02/06/09、PERF-C1/H1、MNT-L1、B7/B13/B14）可见经过多轮迭代优化，非一次性产物。

**主要风险**：双轨 DB 设计、SQLite 高并发瓶颈、单例 DI 可测试性差、覆盖率门槛偏低、e2e 未纳入 CI、可观测性不足、部分 spec 未完成验证。这些是「成熟项目向生产规模化演进」的典型障碍，而非致命缺陷。

**适用场景**：单作者桌面创作（Tauri + 本地 Ollama）或小团队 Web 部署（Fly.io 单实例）。不建议直接用于多租户高并发 SaaS 场景，需先解决 SQLite → PostgreSQL 迁移、认证体系升级、可观测性建设。

---

> 本 Wiki 基于代码仓库快照生成，如代码演进请同步更新。建议补充：API 参考文档、ADR 架构决策记录、部署运维手册。
