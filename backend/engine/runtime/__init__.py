"""engine/runtime — 守护进程运行时（借鉴 PlotPilot engine/runtime）

包含：
- CircuitBreaker: 熔断器（连续失败达阈值后打开，暂停后半开重试）
- daemon_loop: 守护进程主循环（心跳 + 活跃小说发现 + 异常隔离）
- engine_daemon: EngineDaemon 统一入口（包装 AutonomousWritingEngine）
"""
