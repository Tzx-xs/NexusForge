import os
import threading
from typing import ClassVar, Optional

from agents.agent_engine import WritingAgent
from agents.tools.registry import ToolRegistry
from application.audit.audit_service import QualityAuditService
from application.engine.autonomous_writer import AutonomousWritingEngine
from application.engine.context_budget_allocator import ContextBudgetAllocator
from application.engine.context_builder import ContextBuilder
from application.engine.generation_pipeline import GenerationPipeline
from application.engine.prompt_manager import PromptManager
from application.memory.memory_engine import MemoryEngine
from application.services.bible_service import BibleService
from application.services.chapter_service import ChapterService
from application.services.export_service import ExportService
from application.services.novel_service import NovelService
from application.services.review_service import ReviewService
from application.services.review_task_service import ReviewTaskService
from application.services.search_service import SearchService
from application.services.settings_service import SettingsService
from application.voice.voice_service import VoiceService
from config.logging import get_logger
from config.settings import Settings
from engine.pipeline.aftermath import AftermathPipeline
from engine.pipeline.base import StoryPipeline
from infrastructure.ai.chromadb_vector_store import ChromaDBVectorStore, SimpleVectorStore
from infrastructure.ai.embedding_service import EmbeddingService
from infrastructure.ai.llm_client import LLMClient
from infrastructure.ai.provider_factory import create_llm_client, create_llm_client_from_dict
from infrastructure.ai.vector_store import BaseVectorStore
from infrastructure.persistence.chapter_repo import ChapterRepository
from infrastructure.persistence.character_repo import CharacterRepository
from infrastructure.persistence.conversation_repo import ConversationRepository
from infrastructure.persistence.database import Database
from infrastructure.persistence.foreshadow_repo import ForeshadowRepository
from infrastructure.persistence.knowledge_repo import KnowledgeRepository
from infrastructure.persistence.memory_repo import MemoryRepository
from infrastructure.persistence.novel_repo import NovelRepository
from infrastructure.persistence.review_repo import ReviewRepository
from infrastructure.persistence.review_task_repo import ReviewTaskRepository
from infrastructure.persistence.setting_repo import SettingRepository
from infrastructure.persistence.snapshot_repo import SnapshotRepository
from infrastructure.persistence.storyline_repo import StorylineRepository
from infrastructure.persistence.voice_repo import VoiceRepository

logger = get_logger(__name__)


class Container:
    _instance: ClassVar[Optional["Container"]] = None

    def __init__(self) -> None:
        self.settings = Settings.get_instance()
        self._reload_lock = threading.Lock()
        self._init_db()
        self._init_repos()
        # settings_service 初始化后才能读取数据库配置
        self.settings_service = SettingsService(setting_repo=self.setting_repo)
        self._init_ai()
        self._init_engine()
        self._init_services()

    def _init_db(self) -> None:
        db_path = self.settings.db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = Database(db_path)

    def _init_repos(self) -> None:
        self.novel_repo = NovelRepository(self.db)
        self.chapter_repo = ChapterRepository(self.db)
        self.character_repo = CharacterRepository(self.db)
        self.setting_repo = SettingRepository(self.db)
        self.review_repo = ReviewRepository(self.db)
        self.review_task_repo = ReviewTaskRepository(self.db)
        self.memory_repo = MemoryRepository(self.db)
        self.knowledge_repo = KnowledgeRepository(self.db)
        self.foreshadow_repo = ForeshadowRepository(self.db)
        self.snapshot_repo = SnapshotRepository(self.db)
        self.storyline_repo = StorylineRepository(self.db)
        self.voice_repo = VoiceRepository(self.db)
        self.conversation_repo = ConversationRepository(self.db)

    def _build_llm_client(self) -> LLMClient:
        """优先使用数据库中的设置构建 LLM 客户端，数据库为空时回退到环境变量。"""
        try:
            db_settings = self.setting_repo.get_system_settings()
            if db_settings.get("ai_provider") or db_settings.get("api_key") or db_settings.get("default_model"):
                # 解密 api_key 再传给工厂函数
                if db_settings.get("api_key"):
                    db_settings["api_key"] = self.setting_repo.get_decrypted_api_key()
                return create_llm_client_from_dict(db_settings)
        except Exception as e:
            logger.warning("从数据库加载LLM配置失败，回退到环境变量: %s", e)
        return create_llm_client(self.settings)

    def _init_ai(self) -> None:
        self.llm_client = self._build_llm_client()
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "infrastructure", "ai", "prompts")
        self.prompt_manager = PromptManager(prompts_dir=prompts_dir)
        if self.settings.api_key:
            self.embedding_service = EmbeddingService(
                provider="openai",
                api_key=self.settings.api_key,
                model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
                base_url=self.settings.api_base_url,
            )
        else:
            self.embedding_service = EmbeddingService(provider="simple")
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        vector_path = os.path.join(data_dir, "vector_store.json")
        self.vector_store: BaseVectorStore
        try:
            # M-16: 注入 embedding_function 到 ChromaDBVectorStore 确保维度一致
            chroma_ef = self.embedding_service.as_chromadb_ef()
            self.vector_store = ChromaDBVectorStore(
                persist_directory=os.path.join(data_dir, "chroma"),
                embedding_function=chroma_ef,
            )
            if not hasattr(self.vector_store, "_available") or not self.vector_store._available:
                self.vector_store = SimpleVectorStore(storage_path=vector_path)
        except Exception:
            self.vector_store = SimpleVectorStore(storage_path=vector_path)

    def _init_engine(self) -> None:
        self.context_budget_allocator = ContextBudgetAllocator(total_budget=6000)
        self.context_builder = ContextBuilder(
            novel_repo=self.novel_repo,
            chapter_repo=self.chapter_repo,
            character_repo=self.character_repo,
            setting_repo=self.setting_repo,
            vector_store=self.vector_store,
            budget_allocator=self.context_budget_allocator,
        )
        self.memory_engine = MemoryEngine(
            memory_repo=self.memory_repo,
            knowledge_repo=self.knowledge_repo,
            character_repo=self.character_repo,
            chapter_repo=self.chapter_repo,
        )
        self.quality_audit_service = QualityAuditService.with_default_guards()
        self.voice_service = VoiceService(voice_repo=self.voice_repo)
        self.aftermath_pipeline = AftermathPipeline(
            knowledge_repo=self.knowledge_repo,
            memory_repo=self.memory_repo,
            llm_client=self.llm_client,
            prompt_manager=self.prompt_manager,
            vector_store=self.vector_store,
            chapter_repo=self.chapter_repo,
            snapshot_repo=self.snapshot_repo,
        )
        # Sprint 2.2：注入 AftermathPipeline，让 SSE 路径也触发章后管线
        self.generation_pipeline = GenerationPipeline(
            llm_client=self.llm_client,
            prompt_manager=self.prompt_manager,
            context_builder=self.context_builder,
            chapter_repo=self.chapter_repo,
            review_repo=self.review_repo,
            aftermath_pipeline=self.aftermath_pipeline,
            max_retries=self.settings.generation_max_retries,
        )
        self.story_pipeline = StoryPipeline(
            chapter_repo=self.chapter_repo,
            novel_repo=self.novel_repo,
            context_builder=self.context_builder,
            memory_engine=self.memory_engine,
            prompt_manager=self.prompt_manager,
            llm_client=self.llm_client,
            quality_service=self.quality_audit_service,
            voice_service=self.voice_service,
            aftermath_pipeline=self.aftermath_pipeline,
        )

    def _init_services(self) -> None:
        self.novel_service = NovelService(
            novel_repo=self.novel_repo,
            chapter_repo=self.chapter_repo,
            character_repo=self.character_repo,
        )
        self.chapter_service = ChapterService(
            chapter_repo=self.chapter_repo,
            novel_repo=self.novel_repo,
            generation_pipeline=self.generation_pipeline,
            story_pipeline=self.story_pipeline,
        )
        self.bible_service = BibleService(
            character_repo=self.character_repo,
            setting_repo=self.setting_repo,
        )
        self.review_service = ReviewService(
            review_repo=self.review_repo,
            chapter_repo=self.chapter_repo,
            llm_client=self.llm_client,
            prompt_manager=self.prompt_manager,
        )
        self.review_task_service = ReviewTaskService(
            review_task_repo=self.review_task_repo,
        )
        self.autonomous_writer = AutonomousWritingEngine(
            chapter_service=self.chapter_service,
            quality_service=self.quality_audit_service,
            voice_service=self.voice_service,
            aftermath_pipeline=self.aftermath_pipeline,
        )
        self.export_service = ExportService(
            novel_repo=self.novel_repo,
            chapter_repo=self.chapter_repo,
            character_repo=self.character_repo,
            setting_repo=self.setting_repo,
        )
        # Sprint 3.2：全局搜索服务（跨 5 表 LIKE 查询）
        self.search_service = SearchService(database=self.db)
        self.tool_registry = ToolRegistry.create_default(
            chapter_service=self.chapter_service,
            review_service=self.review_service,
            bible_service=self.bible_service,
            export_service=self.export_service,
            foreshadow_repo=self.foreshadow_repo,
            llm_client=self.llm_client,
            novel_service=self.novel_service,
        )
        self.writing_agent = WritingAgent(
            llm_client=self.llm_client,
            tool_registry=self.tool_registry,
            conversation_repo=self.conversation_repo,
        )

    def reload_llm_from_db(self) -> bool:
        """从数据库重新加载 LLM 配置并重建所有依赖 LLM 客户端的对象。

        在 Settings API 更新后调用，使用户在 UI 修改的 AI 配置即时生效。
        返回 True 表示成功重建，False 表示失败（旧客户端保持可用）。

        实施细节：将重建工作拆给三个私有方法（engine / services / agent），
        本方法仅负责加载新 LLMClient、调度重建、汇总日志，保证单一职责。
        """
        try:
            db_settings = self.setting_repo.get_system_settings()
            # 解密 api_key
            if db_settings.get("api_key"):
                db_settings["api_key"] = self.setting_repo.get_decrypted_api_key()
            new_client = create_llm_client_from_dict(db_settings)
        except Exception as e:
            logger.error("reload_llm_from_db 失败：无法从数据库配置创建 LLM 客户端，详情: %s", e)
            return False
        self.llm_client = new_client
        logger.info("reload_llm_from_db 成功：已从数据库重建 LLM 客户端")

        rebuilt_services: list[str] = []
        try:
            rebuilt_services.extend(self._reload_engine_components())
            rebuilt_services.extend(self._reload_application_services())
            rebuilt_services.extend(self._reload_agent_components())
        except Exception as e:
            logger.error("reload_llm_from_db 部分失败：LLM 客户端已更新，但服务重建出错: %s", e)
            return False

        self._log_rebuild_summary(rebuilt_services)
        return True

    # ------------------------------------------------------------------
    # reload_llm_from_db 的子步骤（Phase 2.2 拆解）
    # ------------------------------------------------------------------

    def _reload_engine_components(self) -> list[str]:
        """重建依赖 LLMClient 的 engine 层组件。

        Returns:
            已重建组件名列表，供上层汇总日志使用。
        """
        self._init_engine()
        return ["engine (context_builder, generation_pipeline, story_pipeline, aftermath_pipeline)"]

    def _reload_application_services(self) -> list[str]:
        """重建依赖 LLMClient 的应用服务层组件。

        Returns:
            已重建组件名列表。
        """
        rebuilt: list[str] = []
        self.chapter_service = ChapterService(
            chapter_repo=self.chapter_repo,
            novel_repo=self.novel_repo,
            generation_pipeline=self.generation_pipeline,
            story_pipeline=self.story_pipeline,
        )
        rebuilt.append("chapter_service")
        self.review_service = ReviewService(
            review_repo=self.review_repo,
            chapter_repo=self.chapter_repo,
            llm_client=self.llm_client,
            prompt_manager=self.prompt_manager,
        )
        rebuilt.append("review_service")
        self.autonomous_writer = AutonomousWritingEngine(
            chapter_service=self.chapter_service,
            quality_service=self.quality_audit_service,
            voice_service=self.voice_service,
            aftermath_pipeline=self.aftermath_pipeline,
        )
        rebuilt.append("autonomous_writer")
        # M-07: export_service 不直接持有 LLMClient，但依赖 engine 重建后的新状态
        self.export_service = ExportService(
            novel_repo=self.novel_repo,
            chapter_repo=self.chapter_repo,
            character_repo=self.character_repo,
            setting_repo=self.setting_repo,
        )
        rebuilt.append("export_service")
        # M-07: search_service 不直接持有 LLMClient，保持与 engine 一致的重建时序
        self.search_service = SearchService(database=self.db)
        rebuilt.append("search_service")
        return rebuilt

    def _reload_agent_components(self) -> list[str]:
        """重建依赖 LLMClient 的 Agent 层组件（tool_registry + writing_agent）。

        Returns:
            已重建组件名列表。
        """
        rebuilt: list[str] = []
        # 确保 polish_content/analyze_plot 等工具使用新的 LLMClient
        self.tool_registry = ToolRegistry.create_default(
            chapter_service=self.chapter_service,
            review_service=self.review_service,
            bible_service=self.bible_service,
            export_service=self.export_service,
            foreshadow_repo=self.foreshadow_repo,
            llm_client=self.llm_client,
            novel_service=self.novel_service,
        )
        rebuilt.append("tool_registry")
        self.writing_agent = WritingAgent(
            llm_client=self.llm_client,
            tool_registry=self.tool_registry,
            conversation_repo=self.conversation_repo,
        )
        rebuilt.append("writing_agent")
        return rebuilt

    def _log_rebuild_summary(self, rebuilt_services: list[str]) -> None:
        """统一记录 reload_llm_from_db 完成日志。"""
        logger.info(
            "reload_llm_from_db 完成：所有依赖 LLM 的服务已重建 (%s)",
            ", ".join(rebuilt_services),
        )

    @classmethod
    def get_instance(cls) -> "Container":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
