"""统一 API 响应工具。

L-01 修复：抽取原 6 个 API 模块中重复定义的 success_response 函数。
旧实现各自维护同名函数，违反 DRY 原则，修改响应格式需要多处同步改动。
安全实践：响应结构应集中管理，保证一致性便于客户端解析与异常处理。
"""
from typing import Any


def success_response(data: Any) -> dict[str, Any]:
    """构造统一的成功响应结构。

    Args:
        data: 任意可序列化的业务数据

    Returns:
        {"code": 0, "message": "success", "data": data}
    """
    return {"code": 0, "message": "success", "data": data}
