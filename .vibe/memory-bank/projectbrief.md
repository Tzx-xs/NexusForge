# Project Brief — NexusForge (星渊笔)

## Core Purpose
NexusForge（星渊笔）是一个 **本地部署、隐私优先** 的 AI 长篇小说创作引擎。前端使用 PlotPilot UI（Vue 3 + Vite + Pinia + Tauri 2），后端使用 Python（FastAPI + SQLite + Alembic），通过统一的 OpenAI-compatible HTTP 代理连接任意 LLM 服务（OpenAI / Anthropic / Ollama / 任意兼容端点）。

## Key Goals
1. **每章 5-10 次 LLM 调用**（大纲→生成→审查→改写→章后抽取），支持断点续写
2. **六层安全防护**：输入消毒 / 提示词防注入 / 输出校验 / 工具链参数校验 / 文件系统访问控制 / SSRF 防护
3. **15 条写作红线**：自动检测情绪直接命名、陈词滥调、信息倾销等常见问题
4. **知识图谱记忆**：三元组 + 章节摘要 + 向量检索，确保角色/伏笔/设定跨章节一致
5. **快照与回滚**：每章生成后自动创建快照，支持版本回溯与选择性回滚
6. **多视角文风指纹**：自动提取写作风格指纹，检测并纠正文风漂移
7. **完全本地化**：数据存储在本地 SQLite + JSON 文件，无外部依赖（LLM 除外）

## Core Requirements
- Python 3.10+，FastAPI，SQLite，Alembic
- 前端 PlotPilot UI（Vue 3.5+，Vite 6+，Pinia，Tauri 2）
- LLM 通过 OpenAI-compatible API 连接（支持 OpenAI / Anthropic / Ollama）
- 可选依赖：ChromaDB（向量检索）、tiktoken（精确 Token 计数）、cryptography（API Key 加密）
