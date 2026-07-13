from __future__ import annotations

from config.logging import get_logger

logger = get_logger(__name__)

# 压缩阈值（Token 估算）
COMPRESSION_THRESHOLD = 4000


def estimate_tokens(text: str) -> int:
    """粗略估算文本 Token 数（中英文混合约 1 Token ≈ 2 字符）"""
    return len(text) // 2


class MemoryCompressor:
    """对话记忆压缩器

    当对话历史 Token 数超过阈值时，对早期消息做 LLM 摘要压缩。
    保留关键决策信息（角色设定变更、章节重写指令、关键决策），
    丢弃冗余闲聊和重复确认。
    """

    def __init__(self, llm_client):
        """llm_client: 具备 chat() 方法的 LLM 客户端"""
        self.llm_client = llm_client

    def needs_compression(self, messages: list[dict[str, str]]) -> bool:
        """检查是否需要对消息列表进行压缩"""
        total_text = "".join(m.get("content", "") for m in messages)
        return estimate_tokens(total_text) >= COMPRESSION_THRESHOLD

    async def compress(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """压缩消息列表

        提取前 50% 的消息做 LLM 摘要，保留关键决策信息。
        返回压缩后的消息列表（system 摘要 + 后 50% 原始消息）。
        """
        if not self.needs_compression(messages):
            return messages

        split_idx = len(messages) // 2
        early_messages = messages[:split_idx]
        recent_messages = messages[split_idx:]

        summary = await self._summarize(early_messages)

        # 压缩后的消息：摘要作为 system 消息 + 后半部分原始消息
        compressed: list[dict[str, str]] = [{"role": "system", "content": f"[对话摘要] {summary}"}]
        compressed.extend(recent_messages)
        return compressed

    async def _summarize(self, messages: list[dict[str, str]]) -> str:
        """调用 LLM 生成对话摘要

        保留：角色设定变更、章节重写指令、关键决策
        丢弃：冗余闲聊、重复确认
        """
        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )

        prompt = f"""请对以下对话内容做摘要压缩，只保留关键信息：

对话内容：
{conversation_text}

请只保留以下类型的信息：
1. 角色设定变更（新增/修改/删除角色）
2. 章节重写指令（要求重写哪些章节）
3. 关键创作决策（大纲调整、剧情方向变更）
4. 重要用户反馈（明确指出需要改进的地方）

丢弃：
- 冗余闲聊
- 重复确认
- 工具调用过程中的中间结果

请用 2-3 句话生成摘要。"""

        try:
            result = await self.llm_client.chat([
                {"role": "user", "content": prompt}
            ])
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.warning(f"Memory compression failed: {e}")
            # 降级：返回原始消息的简单截断
            return f"前 {len(messages)} 条消息（压缩失败，已保留近一半对话）"
