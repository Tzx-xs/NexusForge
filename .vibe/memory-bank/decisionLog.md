# Decision Log — NexusForge

## Key Decisions

### 1. 选择 DDD 三层架构
**时间**: Phase 1  
**决策**: Domain / Application / Infrastructure 三层分离，端口-适配器模式  
**原因**: 长篇小说创作涉及复杂领域逻辑（知识图谱、记忆锁、伏笔追踪），需要清晰的领域边界  
**影响**: 所有数据访问通过 Repository 抽象，LLM 调用通过 Provider 抽象，易于测试和替换

### 2. SQLite 作为主数据库
**时间**: Phase 1  
**决策**: 使用 SQLite + Alembic 迁移，而非 PostgreSQL/MySQL  
**原因**: 本地部署优先，零配置依赖，WAL 模式提供足够并发性能  
**影响**: 数据库文件存储在 `data/novels.db`，通过 PRAGMA 优化并发

### 3. OpenAI-compatible 统一代理
**时间**: Phase 1  
**决策**: 所有 LLM Provider 统一为 OpenAI-compatible API 格式  
**原因**: OpenAI API 已成为事实标准，Anthropic/Ollama 均提供兼容端点  
**影响**: 用户只需配置 base_url + api_key + model，支持任意兼容服务

### 4. 管线式章节生成
**时间**: Phase 1  
**决策**: 7 步管线（大纲→生成→审查→红线→保存→文风→章后），而非单次 LLM 调用  
**原因**: 长篇小说需要多维度质量保障，每步有明确职责  
**影响**: 支持软失败（文风审查失败不阻断）、硬失败（生成失败中断）

### 5. 15 条写作红线本地检查
**时间**: Phase 2  
**决策**: 红线检查完全本地化（正则 + 关键词），不依赖 LLM  
**原因**: 红线检查是高频操作，本地化确保零延迟、零成本  
**影响**: RedLineChecker 支持 15 条规则，包括情绪命名、陈词滥调、信息倾销等

### 6. 统一章后管线（1 次 LLM 调用替代 5 次）
**时间**: Phase 5  
**决策**: UnifiedExtractionStep 单次 LLM 调用同时抽取摘要/三元组/事实/节拍/伏笔  
**原因**: 原 AftermathPipeline 需要 5 次 LLM 调用，延迟和成本过高  
**影响**: 章后处理从 ~25s 降至 ~5s，Token 消耗降低 80%

### 7. 文风漂移检测 + 定向改写闭环
**时间**: Phase 5  
**决策**: 文风指纹多视角特征提取，漂移检测后 LLM 定向改写，最多 3 轮闭环  
**原因**: 长篇连载容易文风漂移，需要自动化纠偏机制  
**影响**: ValidateVoiceStep 集成到主管线，改写后自动回写章节

### 8. Prompt Node 覆写机制
**时间**: Phase 5  
**决策**: PromptRegistry 按 sort_order 加载，PlotPilot 节点可覆盖 StellarScribe 同名节点  
**原因**: PlotPilot 前端需要定制化提示词，但 StellarScribe 独有节点需保留  
**影响**: sort_order: StellarScribe=5, PlotPilot=10+，后加载的覆盖先加载的

### 9. 快照 gzip 压缩
**时间**: Phase 4  
**决策**: 章节内容 > 10KB 时自动 gzip 压缩后 base64 编码存储  
**原因**: SQLite 存储大文本效率低，压缩可减少 60-80% 存储空间  
**影响**: SnapshotRepository.create() 自动压缩，get_content() 自动解压

### 10. API Key AES-GCM 加密
**时间**: Phase 2  
**决策**: API Key 存储使用 AES-GCM 加密，密钥来源环境变量 ENCRYPTION_KEY  
**原因**: 本地部署场景下 API Key 明文存储存在安全风险  
**影响**: 开发模式机器派生密钥兜底，生产环境必须显式设置 ENCRYPTION_KEY
