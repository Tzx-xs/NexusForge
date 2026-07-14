# Progress — NexusForge

## What Has Been Done
1. **架构设计与实现** — DDD 三层架构（Domain / Application / Infrastructure），端口-适配器模式
2. **LLM Provider 系统** — 统一 OpenAI-compatible 代理，支持 OpenAI / Anthropic / Ollama / Local（mock）
3. **管线系统** — 7 步主管线（大纲→生成→审查→红线→保存→文风→章后），支持软失败与硬失败
4. **章后管线** — 旧版（5 次 LLM）+ 新版（1 次 LLM 统一抽取），输出到 `backend/output/`
5. **六层安全防护** — SSRF 防护、API Key AES-GCM 加密、AI 提示词注入检测、输出校验
6. **记忆锁系统** — FactLock / BeatLock / ClueLock（伏笔），跨章节知识图谱
7. **知识图谱** — 三元组抽取（Subject-Predicate-Object），章节摘要，向量检索
8. **快照系统** — 增量快照、gzip 压缩存储、版本回滚
9. **文风指纹** — 多视角特征提取、漂移检测、LLM 定向改写闭环
10. **自主写作引擎** — 事件驱动守护进程，熔断器，断点续写
11. **前端集成** — PlotPilot UI，SSE 流式通信，进度追踪

## What's Left
- Memory Bank 已初始化完毕
- 系统处于可交付状态

## Known Issues
- ChromaDB 为可选依赖，未安装时自动降级为 SimpleVectorStore（n-gram 相似度）
- LocalProvider 仅用于开发测试，生产环境必须配置真实 LLM Provider
- `tiktoken` 未安装时 Token 计数降级为中英文比例估算
