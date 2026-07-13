"""SSE 异常脱敏工具模块。

为 SSE 流中捕获的异常提供脱敏处理：
- 生产环境返回固定脱敏消息，防止内部路径/配置泄露
- 开发环境返回原始异常信息，便于调试
"""
from config.settings import Settings


def sanitize_error(error: Exception) -> str:
    """生产环境返回脱敏消息，开发环境返回原始异常。

    Args:
        error: 捕获的异常对象

    Returns:
        脱敏后的错误消息字符串
    """
    settings = Settings.get_instance()
    if settings.debug:
        return str(error)
    return "服务器内部错误"
