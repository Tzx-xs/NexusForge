"""EngineDaemon 守护进程测试

验证：
1. CircuitBreaker 熔断器：连续失败达阈值后打开，暂停后可半开重试
2. DaemonLoop 主循环：心跳写入、活跃小说发现、异常隔离
3. EngineDaemon 入口：包装 AutonomousWritingEngine，提供 run_forever
"""
import time
import pytest

from engine.runtime.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    """熔断器测试"""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, wait_seconds=5)
        assert cb.state == CircuitState.CLOSED
        assert cb.is_open() is False

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, wait_seconds=5)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_open() is True

    def test_success_resets_counter(self):
        cb = CircuitBreaker(failure_threshold=3, wait_seconds=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_after_wait(self):
        cb = CircuitBreaker(failure_threshold=2, wait_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open() is True
        time.sleep(0.15)
        assert cb.is_open() is False
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(failure_threshold=2, wait_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        cb.is_open()  # 触发半开
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=2, wait_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        cb.is_open()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_wait_seconds_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, wait_seconds=10)
        cb.record_failure()
        assert cb.is_open() is True
        # 刚打开时剩余等待接近 10s（允许微小耗时）
        assert 8 <= cb.wait_seconds() <= 10


class TestEngineDaemonLoop:
    """守护进程主循环测试（用桩 host）"""

    @pytest.mark.asyncio
    async def test_loop_processes_active_novels(self):
        """有活跃小说时被处理"""
        from engine.runtime.daemon_loop import run_daemon_loop_once
        from engine.runtime.engine_daemon import EngineDaemon

        processed = []

        class StubNovel:
            def __init__(self, novel_id):
                self.novel_id = novel_id

        class StubHost:
            poll_interval = 0
            circuit_breaker = CircuitBreaker(failure_threshold=99)
            _heartbeat_count = 0

            def _write_daemon_heartbeat(self):
                self._heartbeat_count += 1

            def _get_active_novels(self):
                return [StubNovel("n1"), StubNovel("n2")]

            def _cleanup_stale_stop_signals(self, novels):
                pass

            async def _process_novel(self, novel):
                processed.append(novel.novel_id)

        host = StubHost()
        await run_daemon_loop_once(host)

        assert host._heartbeat_count == 1
        assert processed == ["n1", "n2"]

    @pytest.mark.asyncio
    async def test_loop_skips_when_circuit_open(self):
        """熔断器打开时跳过小说处理"""
        from engine.runtime.daemon_loop import run_daemon_loop_once

        processed = []

        class StubHost:
            poll_interval = 0
            circuit_breaker = CircuitBreaker(failure_threshold=1, wait_seconds=60)
            _heartbeat_count = 0

            def _write_daemon_heartbeat(self):
                self._heartbeat_count += 1

            def _get_active_novels(self):
                return ["n1"]

            def _cleanup_stale_stop_signals(self, novels):
                pass

            async def _process_novel(self, novel):
                processed.append(novel)

        host = StubHost()
        host.circuit_breaker.record_failure()  # 打开熔断器
        await run_daemon_loop_once(host)

        # 心跳仍写入，但小说未处理
        assert host._heartbeat_count == 1
        assert processed == []

    @pytest.mark.asyncio
    async def test_loop_isolates_novel_exception(self):
        """单本小说异常不影响其他小说处理"""
        from engine.runtime.daemon_loop import run_daemon_loop_once

        processed = []

        class StubHost:
            poll_interval = 0
            circuit_breaker = CircuitBreaker(failure_threshold=99)
            _heartbeat_count = 0

            def _write_daemon_heartbeat(self):
                self._heartbeat_count += 1

            def _get_active_novels(self):
                return ["n1", "n2", "n3"]

            def _cleanup_stale_stop_signals(self, novels):
                pass

            async def _process_novel(self, novel):
                if novel == "n2":
                    raise RuntimeError("boom")
                processed.append(novel)

        host = StubHost()
        # run_daemon_loop_once 应隔离异常
        await run_daemon_loop_once(host)

        assert "n1" in processed
        assert "n2" not in processed
        assert "n3" in processed


class TestEngineDaemonEntry:
    """EngineDaemon 入口类测试"""

    def test_engine_daemon_creation(self):
        """EngineDaemon 可实例化（包装 AutonomousWritingEngine）"""
        from engine.runtime.engine_daemon import EngineDaemon

        daemon = EngineDaemon(poll_interval=5)
        assert daemon.poll_interval == 5
        assert daemon.circuit_breaker is not None
        assert daemon.circuit_breaker.state == CircuitState.CLOSED
