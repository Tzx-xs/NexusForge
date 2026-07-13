class DomainException(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# =============================================================================
# E1xxx — 资源层异常
# =============================================================================

class NovelNotFoundException(DomainException):
    def __init__(self) -> None:
        super().__init__("E1001", "小说不存在")


class ChapterNotFoundException(DomainException):
    def __init__(self) -> None:
        super().__init__("E1002", "章节不存在")


class CharacterNotFoundException(DomainException):
    def __init__(self) -> None:
        super().__init__("E1003", "人物不存在")


class SettingNotFoundException(DomainException):
    def __init__(self) -> None:
        super().__init__("E1004", "设定不存在")


class SnapshotNotFoundException(DomainException):
    def __init__(self) -> None:
        super().__init__("E1005", "快照不存在")


class ReviewTaskNotFoundException(DomainException):
    def __init__(self) -> None:
        super().__init__("E1006", "审查任务不存在")


# =============================================================================
# E2xxx — LLM 层异常
# =============================================================================

class LLMException(DomainException):
    def __init__(self, message: str = "LLM 调用失败") -> None:
        super().__init__("E2001", message)


class LLMTimeoutException(DomainException):
    def __init__(self) -> None:
        super().__init__("E2002", "LLM 请求超时")


class LLMConnectionException(DomainException):
    def __init__(self) -> None:
        super().__init__("E2004", "LLM 连接失败")


class LLMRateLimitException(DomainException):
    def __init__(self) -> None:
        super().__init__("E2005", "LLM 频率限制")


class PromptNotFoundException(DomainException):
    def __init__(self, prompt_name: str) -> None:
        super().__init__("E2003", f"提示词模板不存在: {prompt_name}")


# =============================================================================
# E3xxx — 业务逻辑层异常
# =============================================================================

class ValidationException(DomainException):
    def __init__(self, message: str = "参数校验失败") -> None:
        super().__init__("E3001", message)


class GenerationInProgressException(DomainException):
    def __init__(self) -> None:
        super().__init__("E3002", "生成进行中，不可重复触发")


# =============================================================================
# E4xxx — 系统/会话层异常
# =============================================================================

class ConfigException(DomainException):
    def __init__(self, message: str = "配置错误") -> None:
        super().__init__("E4001", message)


class ConversationNotFoundException(DomainException):
    """会话不存在（agent_engine 使用 E4004）"""

    def __init__(self, conversation_id: str = "") -> None:
        super().__init__("E4004", f"会话不存在: {conversation_id}" if conversation_id else "会话不存在")


class ToolCallLimitExceededException(DomainException):
    """工具调用次数超限（agent_engine 使用 E4005）"""

    def __init__(self, message: str = "工具调用次数过多（已达上限），请简化需求或分步执行") -> None:
        super().__init__("E4005", message)


# =============================================================================
# E5xxx — 内部错误
# =============================================================================

class InternalErrorException(DomainException):
    """内部错误（agent_engine 使用 E5000）"""

    def __init__(self, message: str = "服务器内部错误") -> None:
        super().__init__("E5000", message)


# =============================================================================
# Agent 层异常
# =============================================================================

class AgentException(DomainException):
    """Agent 层异常基类"""

    def __init__(self, message: str = "Agent 执行异常") -> None:
        super().__init__("E6001", message)


class ToolNotFoundException(AgentException):
    """工具未找到"""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"工具不存在: {tool_name}")


class ToolExecutionException(AgentException):
    """工具执行异常"""

    def __init__(self, tool_name: str, detail: str = "") -> None:
        msg = f"工具 {tool_name} 执行失败"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


# =============================================================================
# 全局错误码注册表
# =============================================================================

# M-22: ERROR_CODES 字典作为 ErrorCodeRegistry 的便捷查询别名，保持向后兼容
# 新增错误码时请在 domain/shared/error_codes.py 的 ErrorCodeRegistry 中注册，
# 此处自动从 Registry 同步。
from domain.shared.error_codes import ErrorCodeRegistry

ERROR_CODES: dict[str, str] = {
    code: entry.message for code, entry in ErrorCodeRegistry.all_codes().items()
}
