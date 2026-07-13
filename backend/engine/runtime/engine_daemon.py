"""EngineDaemon — NexusForge 统一守护进程入口

借鉴 PlotPilot engine/runtime/engine_daemon.py，适配 StellarScribe 架构。

职责：
1. 包装 StellarScribe 现有 AutonomousWritingEngine，提供守护进程模式
2. 实现 DaemonLoopHost 协议（心跳 + 活跃小说发现 + 单本处理）
3. 集成 CircuitBreaker 熔断保护
4. 提供 run_forever 生产入口

与 PlotPilot EngineDaemon 的差异：
- PlotPilot 依赖 StoryPipelineRunner（2361 行 daemon_host）
- NexusForge 包装现有 AutonomousWritingEngine（453 行），渐进式增强
- 心跳写入文件，外部监控可读取
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from config.logging import get_logger

from .circuit_breaker import CircuitBreaker

logger = get_logger(__name__)


class EngineDaemon:
    """NexusForge 剧情引擎守护进程 — start_daemon.py 推荐入口

    用法：
        daemon = EngineDaemon(poll_interval=10)
        daemon.run_forever()

    或单次循环（测试用）：
        await daemon.run_once()
    """

    def __init__(
        self,
        poll_interval: int = 10,
        failure_threshold: int = 5,
        wait_seconds: int = 60,
        heartbeat_path: str | None = None,
        autonomous_writer=None,
    ):
        self.poll_interval = poll_interval
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            wait_seconds=wait_seconds,
        )
        self.heartbeat_path = heartbeat_path or os.path.join(
            os.path.expanduser("~"), ".nexusforge", "daemon.heartbeat"
        )
        # 延迟注入 AutonomousWritingEngine，避免循环依赖
        self._autonomous_writer = autonomous_writer
        self._loop_count = 0

    @property
    def autonomous_writer(self):
        """惰性初始化 AutonomousWritingEngine"""
        if self._autonomous_writer is None:
            try:
                from application.engine.autonomous_writer import AutonomousWritingEngine
                self._autonomous_writer = AutonomousWritingEngine()
            except Exception as e:
                logger.warning("AutonomousWritingEngine 初始化失败: %s", e)
                return None
        return self._autonomous_writer

    # ═══════════════════════════════════════════════════════════════
    # DaemonLoopHost 协议实现
    # ═══════════════════════════════════════════════════════════════

    def _write_daemon_heartbeat(self) -> None:
        """写心跳文件，外部监控可读取"""
        self._loop_count += 1
        try:
            os.makedirs(os.path.dirname(self.heartbeat_path), exist_ok=True)
            heartbeat = {
                "pid": os.getpid(),
                "loop_count": self._loop_count,
                "timestamp": time.time(),
                "circuit_state": self.circuit_breaker.state.value,
                "failure_count": self.circuit_breaker.failure_count,
            }
            with open(self.heartbeat_path, "w", encoding="utf-8") as f:
                json.dump(heartbeat, f, ensure_ascii=False)
        except Exception as e:
            logger.debug("心跳写入失败: %s", e)

    def _get_active_novels(self) -> list:
        """获取活跃小说列表（status=generating 的小说）"""
        writer = self.autonomous_writer
        if writer is None:
            return []
        try:
            # 通过 novel_repo 查询状态为 active 的小说
            novel_repo = getattr(writer, "novel_repo", None)
            if novel_repo is None:
                return []
            # 查询所有 status 为 "generating" 或 "active" 的小说
            novels = []
            if hasattr(novel_repo, "list_active"):
                novels = novel_repo.list_active()
            elif hasattr(novel_repo, "list_all"):
                all_novels = novel_repo.list_all()
                novels = [
                    n for n in all_novels
                    if getattr(n, "status", "") in ("generating", "active", "writing")
                ]
            return novels
        except Exception as e:
            logger.error("获取活跃小说失败: %s", e, exc_info=True)
            return []

    def _cleanup_stale_stop_signals(self, active_novels: list) -> None:
        """清理过期停止信号（占位，后续接入停止信号系统）"""
        pass

    async def _process_novel(self, novel: Any) -> None:
        """处理单本小说：推进一章"""
        writer = self.autonomous_writer
        if writer is None:
            return
        novel_id = getattr(getattr(novel, "novel_id", None), "value", None) or getattr(novel, "id", None) or str(novel)
        logger.info("处理小说: %s", novel_id)
        # 委托给 AutonomousWritingEngine 推进一章
        try:
            if hasattr(writer, "run_single_chapter"):
                await writer.run_single_chapter(novel_id)
            elif hasattr(writer, "generate_chapter"):
                await writer.generate_chapter(novel_id)
        except Exception as e:
            logger.error("小说 %s 章节生成失败: %s", novel_id, e)
            raise

    # ═══════════════════════════════════════════════════════════════
    # 入口方法
    # ═══════════════════════════════════════════════════════════════

    async def run_once(self) -> None:
        """执行单次循环（测试用）"""
        from .daemon_loop import run_daemon_loop_once
        await run_daemon_loop_once(self)

    def run_forever(self) -> None:
        """守护进程无限循环（生产入口）"""
        from .daemon_loop import run_daemon_loop
        banner = (
            f"EngineDaemon Started (NexusForge)\n"
            f"  Poll interval: {self.poll_interval}s\n"
            f"  Circuit breaker: threshold={self.circuit_breaker.failure_threshold}, "
            f"wait={self.circuit_breaker.wait_seconds_total}s\n"
            f"  Heartbeat: {self.heartbeat_path}"
        )
        logger.info("=" * 80)
        logger.info(banner)
        logger.info("=" * 80)
        run_daemon_loop(self)
