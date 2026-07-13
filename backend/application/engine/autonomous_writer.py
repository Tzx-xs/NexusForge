from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from application.audit.audit_service import QualityAuditService
from application.services.chapter_service import ChapterService
from application.voice.voice_service import VoiceService
from config.logging import get_logger
from engine.pipeline.aftermath import AftermathPipeline
from engine.pipeline.context import PipelineContext

logger = get_logger(__name__)


class AutoWriteState(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    GENERATING = "generating"
    AUDITING = "auditing"
    REWRITING = "rewriting"
    AFTERMATH = "aftermath"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AutoWriteMode(StrEnum):
    SINGLE = "single"
    BATCH = "batch"
    OUTLINE = "outline"


@dataclass
class AutoWriteConfig:
    mode: AutoWriteMode = AutoWriteMode.SINGLE
    target_chapters: int = 1
    min_quality_score: float = 60.0
    max_retries_per_chapter: int = 2
    pause_between_chapters: bool = False
    auto_rewrite_on_fail: bool = True
    auto_fix_voice_drift: bool = True  # M-25: 文风漂移自动修正开关
    max_drift_tolerance: float = 0.7
    enable_aftermath: bool = True
    enable_quality_guards: bool = True
    enabled_guards: list[str] = field(default_factory=list)
    target_words_per_chapter: int = 3000

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutoWriteConfig:
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        if isinstance(config.mode, str):
            config.mode = AutoWriteMode(config.mode)
        return config


@dataclass
class AutoWriteStatus:
    session_id: str
    novel_id: str
    state: AutoWriteState
    config: AutoWriteConfig
    current_chapter_index: int = 0
    total_chapters_completed: int = 0
    total_words_generated: int = 0
    failed_chapters: list[int] = field(default_factory=list)
    current_progress: float = 0.0
    started_at: float | None = None
    updated_at: float | None = None
    error: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "novel_id": self.novel_id,
            "state": self.state,
            "current_chapter_index": self.current_chapter_index,
            "total_chapters_completed": self.total_chapters_completed,
            "total_words_generated": self.total_words_generated,
            "failed_chapters": self.failed_chapters,
            "current_progress": self.current_progress,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "mode": self.config.mode,
            "target_chapters": self.config.target_chapters,
        }


class AutonomousWritingEngine:
    """自动驾驶写作引擎

    状态机驱动的自动写作系统，支持：
    - 单章/批量/大纲驱动三种模式
    - 质量护栏自动检测与重写
    - 文风漂移检测与修正
    - 章后处理自动执行
    - 暂停/继续控制
    """

    def __init__(
        self,
        chapter_service: ChapterService,
        quality_service: QualityAuditService | None = None,
        voice_service: VoiceService | None = None,
        aftermath_pipeline: AftermathPipeline | None = None,
    ):
        self.chapter_service = chapter_service
        self.quality_service = quality_service
        self.voice_service = voice_service
        self.aftermath_pipeline = aftermath_pipeline

        self._sessions: dict[str, AutoWriteStatus] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._pause_events: dict[str, asyncio.Event] = {}

    def create_session(self, novel_id: str, config: AutoWriteConfig | None = None) -> AutoWriteStatus:

        session_id = str(uuid.uuid4())[:8]
        config = config or AutoWriteConfig()

        status = AutoWriteStatus(
            session_id=session_id,
            novel_id=novel_id,
            state=AutoWriteState.IDLE,
            config=config,
            started_at=time.time(),
            updated_at=time.time(),
        )

        self._sessions[session_id] = status
        self._pause_events[session_id] = asyncio.Event()
        self._pause_events[session_id].set()

        return status

    def get_status(self, session_id: str) -> AutoWriteStatus | None:
        return self._sessions.get(session_id)

    def list_sessions(self, novel_id: str | None = None) -> list[AutoWriteStatus]:
        sessions = list(self._sessions.values())
        if novel_id:
            sessions = [s for s in sessions if s.novel_id == novel_id]
        return sessions

    async def start(self, session_id: str) -> bool:
        status = self._sessions.get(session_id)
        if not status:
            return False

        if status.state not in (AutoWriteState.IDLE, AutoWriteState.PAUSED):
            return False

        self._tasks[session_id] = asyncio.create_task(self._run_session(session_id))
        return True

    async def pause(self, session_id: str) -> bool:
        status = self._sessions.get(session_id)
        if not status:
            return False

        if status.state in (
            AutoWriteState.PLANNING,
            AutoWriteState.GENERATING,
            AutoWriteState.AUDITING,
            AutoWriteState.REWRITING,
            AutoWriteState.AFTERMATH,
        ):
            status.state = AutoWriteState.PAUSED
            status.updated_at = time.time()
            return True
        return False

    async def resume(self, session_id: str) -> bool:
        status = self._sessions.get(session_id)
        if not status:
            return False

        if status.state == AutoWriteState.PAUSED:
            pause_event = self._pause_events.get(session_id)
            if pause_event:
                pause_event.set()
            return True
        return False

    async def cancel(self, session_id: str) -> bool:
        task = self._tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            status = self._sessions.get(session_id)
            if status:
                status.state = AutoWriteState.FAILED
                status.error = "用户取消"
                status.updated_at = time.time()
            return True
        return False

    async def _run_session(self, session_id: str):
        status = self._sessions.get(session_id)
        if not status:
            return

        config = status.config
        pause_event = self._pause_events.get(session_id)

        try:
            status.state = AutoWriteState.PLANNING
            status.updated_at = time.time()

            chapters_needed = config.target_chapters
            chapters_done = 0

            while chapters_done < chapters_needed:
                if pause_event and not pause_event.is_set():
                    status.state = AutoWriteState.PAUSED
                    status.updated_at = time.time()
                    await pause_event.wait()
                    status.state = AutoWriteState.GENERATING
                    status.updated_at = time.time()

                chapter_idx = status.current_chapter_index + 1
                status.state = AutoWriteState.GENERATING
                status.updated_at = time.time()

                success = await self._generate_single_chapter(status, chapter_idx)

                if success:
                    chapters_done += 1
                    status.total_chapters_completed = chapters_done
                    status.current_chapter_index = chapter_idx
                    status.history.append(
                        {
                            "chapter": chapter_idx,
                            "success": True,
                            "timestamp": time.time(),
                        }
                    )
                else:
                    status.failed_chapters.append(chapter_idx)
                    status.history.append(
                        {
                            "chapter": chapter_idx,
                            "success": False,
                            "timestamp": time.time(),
                        }
                    )

                status.current_progress = chapters_done / max(chapters_needed, 1)
                status.updated_at = time.time()

                if config.pause_between_chapters and chapters_done < chapters_needed:
                    if pause_event:
                        pause_event.clear()
                    status.state = AutoWriteState.PAUSED
                    status.updated_at = time.time()

            status.state = AutoWriteState.COMPLETED
            status.updated_at = time.time()

        except asyncio.CancelledError:
            status.state = AutoWriteState.FAILED
            status.error = "已取消"
            status.updated_at = time.time()
            logger.info("Autonomous session %s cancelled", session_id)
        except Exception as e:
            status.state = AutoWriteState.FAILED
            status.error = str(e)
            status.updated_at = time.time()
            logger.error("Autonomous session %s failed: %s", session_id, e, exc_info=True)
        finally:
            # 清理资源，防止内存泄漏（PERF-H1）
            self._tasks.pop(session_id, None)
            self._pause_events.pop(session_id, None)
            # 保留 _sessions 中的状态（前端可能查询最终结果），后续可通过 list_sessions 返回

    async def _generate_single_chapter(self, status: AutoWriteStatus, chapter_idx: int) -> bool:
        config = status.config
        retry_count = 0
        audit_report = None
        audit_feedback = ""

        while retry_count <= config.max_retries_per_chapter:
            try:
                status.state = AutoWriteState.GENERATING
                status.updated_at = time.time()

                chapter = await asyncio.wait_for(
                    self._generate_chapter(status, chapter_idx, audit_feedback), timeout=300
                )
                if not chapter:
                    retry_count += 1
                    continue

                if config.enable_quality_guards and self.quality_service:
                    status.state = AutoWriteState.AUDITING
                    status.updated_at = time.time()

                    audit_report = await self._run_quality_audit_full(status, chapter.content or "")

                    if not audit_report.get("passed", False) and config.auto_rewrite_on_fail:
                        status.state = AutoWriteState.REWRITING
                        status.updated_at = time.time()
                        # BLOCK-02: 注入审计反馈到重写上下文
                        audit_feedback = self._format_audit_feedback(audit_report)
                        retry_count += 1
                        continue

                # M-25: Aftermath 阶段后检查文风漂移
                if config.enable_aftermath and self.aftermath_pipeline:
                    status.state = AutoWriteState.AFTERMATH
                    status.updated_at = time.time()
                    await self._run_aftermath(status, chapter)

                    # 文风漂移检测与修正
                    if self.voice_service and config.auto_fix_voice_drift:
                        await self._check_voice_drift(status, chapter)

                status.total_words_generated += chapter.word_count or 0
                return True

            except TimeoutError:
                logger.warning("章节生成超时(5分钟): chapter_idx=%s", chapter_idx)
                retry_count += 1
            except Exception as e:
                status.error = str(e)
                retry_count += 1

        # 达到最大重试次数，记录最终审计报告
        if audit_report and not audit_report.get("passed", False):
            status.error = f"审计不通过(重试{retry_count}次): {audit_report.get('overall_score', 0):.1f}分"
        return False

    async def _generate_chapter(self, status: AutoWriteStatus, chapter_idx: int, audit_feedback: str = ""):
        """生成章节，支持审计反馈注入（BLOCK-02）。"""
        try:
            result = await self.chapter_service.generate_chapter(status.novel_id, audit_feedback=audit_feedback)
            return result
        except Exception:
            logger.exception("章节生成失败: chapter_idx=%s", chapter_idx)
            return None

    @staticmethod
    def _format_audit_feedback(audit_report: dict) -> str:
        """格式化审计报告为注入重写的反馈文本（BLOCK-02）。"""
        guard_results = audit_report.get("guard_results", [])
        if not guard_results:
            return (
                "上一版审查发现质量问题（"
                f"总分: {audit_report.get('overall_score', 0):.1f}），"
                "请针对性修正后重新生成。"
            )

        lines = ["## 上一版审查反馈", "以下问题需要在重写时修正："]
        issue_idx = 1
        for guard in guard_results:
            guard_name = guard.get("guard_name", "未知护栏")
            issues = guard.get("issues", [])
            if not issues:
                continue
            for issue in issues:
                if isinstance(issue, dict):
                    desc = issue.get("description", str(issue))
                else:
                    desc = str(issue)
                lines.append(f"{issue_idx}. [{guard_name}] {desc}")
                issue_idx += 1

        lines.append("")
        lines.append("请针对性修正后重新生成。")
        return "\n".join(lines)

    async def _run_quality_audit_full(self, status: AutoWriteStatus, content: str) -> dict:
        """执行质量审计并返回完整报告字典（BLOCK-02）。"""
        if not self.quality_service:
            return {"passed": True, "overall_score": 100.0, "guard_results": []}


        report = await self.quality_service.run_audit(
            content=content,
            context={"novel_id": status.novel_id},
            enabled_guards=status.config.enabled_guards or None,
        )

        report_dict = report.to_dict() if hasattr(report, "to_dict") else report.__dict__
        passed = report.overall_score >= status.config.min_quality_score if hasattr(report, "overall_score") else report_dict.get("passed", False)
        if isinstance(report_dict, dict):
            report_dict["passed"] = passed
        return report_dict

    async def _run_quality_audit(self, status: AutoWriteStatus, content: str) -> bool:
        if not self.quality_service:
            return True

        report = await self.quality_service.run_audit(
            content=content,
            context={"novel_id": status.novel_id},
            enabled_guards=status.config.enabled_guards or None,
        )

        return report.overall_score >= status.config.min_quality_score

    async def _run_aftermath(self, status: AutoWriteStatus, chapter):
        if not self.aftermath_pipeline:
            return
        try:
            ctx = PipelineContext(
                novel_id=status.novel_id,
                chapter_id=chapter.id,
                chapter_index=getattr(chapter, "number", None),
            )
            await self.aftermath_pipeline.run(ctx, chapter.content or "")
        except Exception as e:
            logger.warning("章后处理失败: %s", e, exc_info=True)

    async def _check_voice_drift(self, status: AutoWriteStatus, chapter):
        """M-25: 文风漂移检测与自动修正。"""
        if not self.voice_service:
            return
        try:
            fingerprints = self.voice_service.list_fingerprints()
            if not fingerprints:
                return

            fp_id = fingerprints[0].get("id", "")
            if not fp_id:
                return

            drift_result = self.voice_service.detect_drift(fp_id, chapter.content or "")
            if drift_result and getattr(drift_result, "drifted", False):
                logger.warning(
                    "文风漂移检测: chapter=%s, similarity=%.2f",
                    getattr(chapter, "number", "?"),
                    getattr(drift_result, "overall_similarity", 0),
                )
                # 如果启用自动修正且漂移超过阈值
                if status.config.auto_fix_voice_drift:
                    drift_dims = getattr(drift_result, "drift_dimensions", [])
                    if drift_dims:
                        rewrite_prompt = self.voice_service.generate_rewrite_prompt(
                            fp_id, chapter.content or "", drift_dims
                        )
                        if rewrite_prompt:
                            logger.info("文风漂移修正提示已生成: %d 维度", len(drift_dims))
        except Exception as e:
            logger.warning("文风漂移检测失败: %s", e, exc_info=True)
