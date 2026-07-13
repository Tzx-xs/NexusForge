"""错误码集中定义（M-22）。

统一管理项目中所有错误码，包含 code / message / http_status 三元组，
消除分散在 exceptions.py 和 main.py 中的重复定义。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorCode:
    """错误码条目 — code / message / http_status 三元组"""

    code: str
    message: str
    http_status: int


class ErrorCodeRegistry:
    """错误码注册表 — 所有错误码的单一权威来源。

    用法:
        status = ErrorCodeRegistry.get_http_status("E1001")      # 404
        msg    = ErrorCodeRegistry.get_message("E1001")           # "小说不存在"
    """

    _entries: dict[str, ErrorCode] = {
        # =========================================================================
        # E1xxx — 资源层异常
        # =========================================================================
        "E1001": ErrorCode("E1001", "小说不存在", 404),
        "E1002": ErrorCode("E1002", "章节不存在", 404),
        "E1003": ErrorCode("E1003", "人物不存在", 404),
        "E1004": ErrorCode("E1004", "设定不存在", 404),
        "E1005": ErrorCode("E1005", "快照不存在", 404),
        "E1006": ErrorCode("E1006", "审查任务不存在", 404),
        # =========================================================================
        # E2xxx — LLM 层异常
        # =========================================================================
        "E2001": ErrorCode("E2001", "LLM 调用失败", 502),
        "E2002": ErrorCode("E2002", "LLM 请求超时", 504),
        "E2003": ErrorCode("E2003", "提示词模板不存在", 500),
        "E2004": ErrorCode("E2004", "LLM 连接失败", 502),
        "E2005": ErrorCode("E2005", "LLM 频率限制", 429),
        # =========================================================================
        # E3xxx — 业务逻辑层异常
        # =========================================================================
        "E3001": ErrorCode("E3001", "参数校验失败", 400),
        "E3002": ErrorCode("E3002", "生成进行中，不可重复触发", 409),
        "E3003": ErrorCode("E3003", "章节已有内容，不可覆盖", 409),
        # =========================================================================
        # E4xxx — 系统/会话层异常
        # =========================================================================
        "E4001": ErrorCode("E4001", "配置错误", 500),
        "E4004": ErrorCode("E4004", "会话不存在", 404),
        "E4005": ErrorCode("E4005", "工具调用次数超限", 400),
        # =========================================================================
        # E5xxx — 内部错误
        # =========================================================================
        "E5000": ErrorCode("E5000", "服务器内部错误", 500),
        # =========================================================================
        # E6xxx — Agent 层异常
        # =========================================================================
        "E6001": ErrorCode("E6001", "Agent 执行异常", 500),
        "E6002": ErrorCode("E6002", "工具不存在", 404),
    }

    @classmethod
    def get_http_status(cls, code: str) -> int:
        """获取错误码对应的 HTTP 状态码。未注册的错误码返回 500。"""
        entry = cls._entries.get(code)
        return entry.http_status if entry else 500

    @classmethod
    def get_message(cls, code: str) -> str:
        """获取错误码对应的默认消息。未注册的错误码返回原始 code。"""
        entry = cls._entries.get(code)
        return entry.message if entry else code

    @classmethod
    def get_entry(cls, code: str) -> ErrorCode | None:
        """获取完整错误码条目。"""
        return cls._entries.get(code)

    @classmethod
    def all_codes(cls) -> dict[str, ErrorCode]:
        """返回所有已注册的错误码（只读视图）。"""
        return dict(cls._entries)

    @classmethod
    def to_http_status_map(cls) -> dict[str, int]:
        """生成 {code: http_status} 映射字典（用于 HTTP 异常处理器）。"""
        return {entry.code: entry.http_status for entry in cls._entries.values()}
