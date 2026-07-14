# Active Context — NexusForge

## Current State
项目已完成 Phase 1-5 的完整开发，包括：
- **Phase 1**: DDD 架构、自主写作引擎、管线系统、记忆锁系统
- **Phase 2**: 六层安全防护、AI 提示词注入检测、SSRF 防护
- **Phase 3**: 角色一致性守卫、知识图谱记忆、三元组抽取
- **Phase 4**: 快照系统、回滚机制、向量检索、ChromaDB 集成
- **Phase 5**: 多视角文风指纹、漂移检测与定向改写、统一章后管线（1 次 LLM 调用替代 5 次）

## Current Focus
系统处于稳定运行状态，代码库完整。所有 `vibe sync` 已完成，Memory Bank 已初始化。

## Key Files & Locations
- **后端入口**: `backend/main.py` (FastAPI app，lifespan 初始化)
- **应用层**: `backend/application/` — service 层，LLM 客户端工厂
- **领域层**: `backend/domain/` — 实体、值对象、异常、仓储接口
- **引擎层**: `backend/engine/` — 自主写作引擎、管线系统、运行时守护进程
- **基础设施**: `backend/infrastructure/` — AI providers、数据库、持久化仓库、安全工具
- **提示词包**: `backend/infrastructure/ai/prompt_packages/` — StellarScribe + PlotPilot 节点
- **前端**: `frontend/` — PlotPilot UI (Vue 3 + Vite + Pinia + Tauri 2)
- **数据库迁移**: `backend/alembic/` — Alembic 迁移管理
- **Memory Bank**: `.vibe/memory-bank/` — 项目记忆文件

## Recent Changes
- 初始化 Memory Bank（首次 `vibe init`）
- 全量代码审查完成，所有文件已读取并分析
