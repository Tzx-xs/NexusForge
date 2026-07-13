"""daemon_loop — 守护进程主循环

借鉴 PlotPilot engine/runtime/daemon_loop.py，适配 StellarScribe 架构。

设计原则：
1. 事务最小化：每轮循环只做"发现活跃小说 → 处理 → 等待"
2. 异常隔离：单本小说处理失败不影响其他小说
3. 心跳写入：每轮循环写心跳，外部可监控守护进程存活
4. 熔断保护：熔断器打开时跳过处理，仅写心跳

提供两个入口：
- run_daemon_loop_once: 单次循环（测试用）
- run_daemon_loop: 无限循环（生产用，调用 run_daemon_loop_once + sleep）
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class DaemonLoopHost(Protocol):
    """守护进程主循环所需的最小 host 接口"""

    poll_interval: int
    circuit_breaker: Any

    def _write_daemon_heartbeat(self) -> None: ...
    def _get_active_novels(self) -> list: ...
    def _cleanup_stale_stop_signals(self, active_novels: list) -> None: ...
    async def _process_novel(self, novel: Any) -> None: ...


async def run_daemon_loop_once(host: DaemonLoopHost) -> None:
    """执行单次守护进程循环

    步骤：
    1. 写心跳
    2. 检查熔断器，打开则跳过处理
    3. 获取活跃小说列表
    4. 逐本处理（异常隔离）
    """
    host._write_daemon_heartbeat()

    if host.circuit_breaker and host.circuit_breaker.is_open():
        wait = host.circuit_breaker.wait_seconds()
        logger.warning("熔断器打开，跳过本轮处理，剩余等待 %.0fs", wait)
        return

    try:
        active_novels = host._get_active_novels()

        if active_novels:
            host._cleanup_stale_stop_signals(active_novels)
            logger.debug("发现 %d 本活跃小说", len(active_novels))

        for novel in active_novels:
            novel_start = time.time()
            try:
                await host._process_novel(novel)
            except Exception as e:
                # 异常隔离：记录但不传播，继续处理下一本
                novel_id = getattr(getattr(novel, "novel_id", None), "value", novel)
                logger.error(
                    "处理小说 %s 时异常: %s",
                    novel_id, e, exc_info=True,
                )
                if host.circuit_breaker:
                    host.circuit_breaker.record_failure()
            else:
                if host.circuit_breaker:
                    host.circuit_breaker.record_success()
                novel_elapsed = time.time() - novel_start
                logger.debug(
                    "   [%s] 处理耗时: %.2fs",
                    getattr(getattr(novel, "novel_id", None), "value", novel),
                    novel_elapsed,
                )

    except Exception as e:
        logger.error("Daemon 循环顶层异常: %s", e, exc_info=True)


def run_daemon_loop(host: DaemonLoopHost, *, banner: str | None = None) -> None:
    """守护进程无限循环（生产入口）

    Args:
        host: 实现 DaemonLoopHost 协议的对象
        banner: 启动横幅日志
    """
    if banner:
        logger.info("=" * 80)
        logger.info(banner)
        logger.info("=" * 80)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop_count = 0
    while True:
        loop_count += 1
        loop_start = time.time()

        try:
            loop.run_until_complete(run_daemon_loop_once(host))
        except Exception as e:
            logger.error("Daemon 顶层异常: %s", e, exc_info=True)

        loop_elapsed = time.time() - loop_start
        if loop_elapsed > host.poll_interval * 2:
            logger.warning("Loop #%s 耗时过长: %.2fs", loop_count, loop_elapsed)

        time.sleep(host.poll_interval)
