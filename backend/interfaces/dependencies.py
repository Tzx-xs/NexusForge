from fastapi import Depends

from agents.agent_engine import WritingAgent
from application.audit.audit_service import QualityAuditService
from application.engine.autonomous_writer import AutonomousWritingEngine
from application.memory.memory_engine import MemoryEngine
from application.services.bible_service import BibleService
from application.services.chapter_service import ChapterService
from application.services.worldview_service import WorldviewService
from application.services.export_service import ExportService
from application.services.novel_service import NovelService
from application.services.review_service import ReviewService
from application.services.review_task_service import ReviewTaskService
from application.services.search_service import SearchService
from application.services.settings_service import SettingsService
from application.voice.voice_service import VoiceService
from infrastructure.persistence.conversation_repo import ConversationRepository
from infrastructure.persistence.foreshadow_repo import ForeshadowRepository
from infrastructure.persistence.knowledge_repo import KnowledgeRepository
from infrastructure.persistence.snapshot_repo import SnapshotRepository
from infrastructure.persistence.storyline_repo import StorylineRepository
from interfaces.container import Container


def get_novel_service() -> NovelService:
    return Container.get_instance().novel_service


def get_chapter_service() -> ChapterService:
    return Container.get_instance().chapter_service


def get_bible_service() -> BibleService:
    return Container.get_instance().bible_service


def get_storyline_repo() -> StorylineRepository:
    return Container.get_instance().storyline_repo


def get_worldview_service(
    bible_service: BibleService = Depends(get_bible_service),
    storyline_repo: StorylineRepository = Depends(get_storyline_repo),
) -> WorldviewService:
    return WorldviewService(bible_service=bible_service, storyline_repo=storyline_repo)


def get_search_service() -> SearchService:
    """Sprint 3.2：全局搜索服务依赖注入。"""
    return Container.get_instance().search_service


def get_review_service() -> ReviewService:
    return Container.get_instance().review_service


def get_review_task_service() -> ReviewTaskService:
    return Container.get_instance().review_task_service


def get_settings_service() -> SettingsService:
    return Container.get_instance().settings_service


def get_memory_engine() -> MemoryEngine:
    return Container.get_instance().memory_engine


def get_knowledge_repo() -> KnowledgeRepository:
    return Container.get_instance().knowledge_repo


def get_foreshadow_repo() -> ForeshadowRepository:
    return Container.get_instance().foreshadow_repo


def get_snapshot_repo() -> SnapshotRepository:
    return Container.get_instance().snapshot_repo


def get_quality_audit_service() -> QualityAuditService:
    return Container.get_instance().quality_audit_service


def get_voice_service() -> VoiceService:
    return Container.get_instance().voice_service


def get_export_service() -> ExportService:
    return Container.get_instance().export_service


def get_autonomous_writer() -> AutonomousWritingEngine:
    return Container.get_instance().autonomous_writer


def get_writing_agent() -> WritingAgent:
    return Container.get_instance().writing_agent


def get_conversation_repo() -> ConversationRepository:
    return Container.get_instance().conversation_repo
