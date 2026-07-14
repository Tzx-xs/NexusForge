# System Patterns — NexusForge

## Architecture Overview
```
┌─────────────────────────────────────────────────────────┐
│  Frontend (PlotPilot UI)                                │
│  Vue 3 + Vite 6 + Pinia + Tauri 2                      │
│  Pages: /novels, /novels/:id/generate, /review          │
│  SSE 流式通信，乐观更新                                  │
└─────────────┬───────────────────────────────────────────┘
              │ HTTP (REST API + SSE)
              ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (main.py)                              │
│  Middleware: SessionMiddleware, ExceptionMiddleware      │
│  Routers: novels, chapters, reviews, settings,          │
│           characters, agents, structure, engine,         │
│           voice, memories, knowledge, snapshots          │
└─────────────┬───────────────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌──────────┐    ┌──────────────────────────────────────┐
│ Application│    │  Infrastructure                      │
│ Services   │    │  ├── AI Providers (OpenAI/Anthropic/ │
│ (LLM调用)  │    │  │              Ollama/Local)        │
│            │    │  ├── LLMClient (重试/流式/JSON解析)   │
└────────────┘    │  ├── PromptManager (YAML模板引擎)    │
                  │  ├── PromptRegistry (可覆写节点)      │
                  │  ├── EmbeddingService (向量嵌入)      │
                  │  ├── VectorStore (ChromaDB/Simple)   │
                  │  ├── Database (SQLite + Alembic)     │
                  │  ├── Repositories (CRUD)             │
                  │  ├── Tools (红线检查/评分/格式校验)    │
                  │  └── Security (SSRF/加密/注入检测)    │
                  └──────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────┐
│  Engine Layer (engine/)                                  │
│  ├── AutonomousWritingEngine (主引擎)                    │
│  ├── PipelineContext (上下文状态机)                       │
│  ├── Pipeline (主管线: 7步)                              │
│  ├── AftermathPipeline / UnifiedAftermathPipeline        │
│  ├── Steps (大纲/生成/审查/红线/保存/文风/章后)           │
│  ├── Runtime (CircuitBreaker + daemon_loop)             │
│  └── SSEBroadcaster (实时推送)                           │
└─────────────────────────────────────────────────────────┘
```

## Key Patterns
1. **Repository Pattern** — 所有数据访问通过 Repository 抽象，底层 SQLite + 原生 sql3
2. **Pipeline Pattern** — 章节生成为 7 步管线，每步返回 StepResult，支持软失败继续
3. **Port-Adapter** — LLM Provider 通过 BaseProvider 抽象，LLMClient 封装重试/流式
4. **Event-Driven Runtime** — 守护进程循环，CircuitBreaker 熔断保护
5. **Prompt Node 覆写** — PromptRegistry 按 sort_order 加载，PlotPilot 节点覆盖 StellarScribe
6. **SSE Push** — 后端通过 SSE Broadcaster 向前端推送实时进度
7. **Snapshot & Rollback** — 每章快照（gzip 压缩），支持版本回溯

## Data Flow (Single Chapter Generation)
```
User clicks "Generate Chapter N"
  → POST /api/engine/generate { novel_id, chapter_index }
  → AutonomousWritingEngine.generate_chapter()
  → PipelineContext 初始化
  → Step 1: BuildOutlineStep (LLM call #1: 大纲生成)
  → Step 2: GenerateContentStep (LLM call #2: 内容生成)
  → Step 3: ValidateContentStep (本地质量审计, Guard-based)
  → Step 4: ValidateRedLinesStep (15条红线本地检查)
  → Step 5: SaveChapterStep (持久化章节)
  → Step 6: ValidateVoiceStep (文风漂移检测 + LLM改写闭环, LLM call #3+)
  → Step 7: RunPostCommitStep → UnifiedAftermathPipeline
    → UnifiedExtractionStep (LLM call #4: 统一抽取8类数据)
    → IndexVectorStep (向量索引)
    → CreateSnapshotStep (快照创建)
  → FinalizeStep (状态置为 COMPLETED)
  → SSE: engine:chapter_completed
```
