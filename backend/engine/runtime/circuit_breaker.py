"""CircuitBreaker — 熔断器

借鉴 PlotPilot 守护进程的熔断保护机制：
- CLOSED: 正常运行，记录失败次数
- OPEN: 失败达阈值后打开，拒绝处理，等待 wait_seconds
- HALF_OPEN: 等待期满后进入半开，允许试探性处理
  - 成功 → 回到 CLOSED
  - 失败 → 回到 OPEN

用法：
    cb = CircuitBreaker(failure_threshold=5, wait_seconds=60)
    if cb.is_open():
        time.sleep(cb.wait_seconds())
        return
    try:
        do_risky_work()
        cb.record_success()
    except Exception:
        cb.record_failure()
"""
from __future__ import annotations

import logging
import time
from enum import StrEnum

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """三态熔断器"""

    def __init__(self, failure_threshold: int = 5, wait_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.wait_seconds_total = wait_seconds
        self.failure_count: int = 0
        self.state: CircuitState = CircuitState.CLOSED
        self._opened_at: float | None = None

    def record_failure(self) -> None:
        """记录一次失败，达阈值后打开熔断器"""
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN:
            # 半开状态失败，立即重新打开
            self._open()
            logger.warning(
                "CircuitBreaker 半开探测失败，重新打开（failures=%d）",
                self.failure_count,
            )
        elif self.failure_count >= self.failure_threshold:
            self._open()
            logger.warning(
                "CircuitBreaker 打开（failures=%d >= threshold=%d）",
                self.failure_count,
                self.failure_threshold,
            )

    def record_success(self) -> None:
        """记录一次成功，重置失败计数并关闭熔断器"""
        self.failure_count = 0
        if self.state != CircuitState.CLOSED:
            logger.info("CircuitBreaker 关闭（恢复正常）")
        self.state = CircuitState.CLOSED
        self._opened_at = None

    def is_open(self) -> bool:
        """熔断器是否打开（拒绝处理）

        若已过等待期，转为半开并返回 False（允许试探）。
        """
        if self.state == CircuitState.CLOSED:
            return False
        if self.state == CircuitState.OPEN:
            if self._opened_at is not None and (time.time() - self._opened_at) >= self.wait_seconds_total:
                self.state = CircuitState.HALF_OPEN
                logger.info("CircuitBreaker 进入半开状态，允许试探")
                return False
            return True
        # HALF_OPEN
        return False

    def wait_seconds(self) -> int:
        """剩余等待秒数（OPEN 状态下）"""
        if self.state != CircuitState.OPEN or self._opened_at is None:
            return 0
        elapsed = time.time() - self._opened_at
        return max(0, int(self.wait_seconds_total - elapsed))

    def _open(self) -> None:
        self.state = CircuitState.OPEN
        self._opened_at = time.time()

    def reset(self) -> None:
        """手动重置（管理操作）"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self._opened_at = None
