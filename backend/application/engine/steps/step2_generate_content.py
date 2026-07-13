from collections.abc import AsyncGenerator
from typing import Any

from .base_step import BaseStep


class Step2GenerateContent(BaseStep):
    name = "generate_content"
    description = "LLM生成正文（流式）"

    async def execute(self, chapter_id: str, context: dict[str, Any]) -> tuple[bool, dict[str, Any], str]:
        """非流式入口：消费 execute_stream 事件流，收集最终结果。

        Sprint 2.4：删除原本与非流式版本重复的死代码，统一委托给 execute_stream。
        GenerationPipeline 实际只调用 execute_stream，但保留 execute 满足 BaseStep 契约。
        """
        outline = ""
        full_content = ""
        async for event, data in self.execute_stream(chapter_id, context):
            if event == "outline":
                outline = data
            elif event == "token":
                full_content += data
            elif event == "content_complete":
                full_content = data
            elif event == "error":
                return False, {"outline": outline}, data

        return True, {
            "outline": outline,
            "content": full_content,
            "word_count": len(full_content),
        }, ""

    async def execute_stream(self, chapter_id: str, context: dict[str, Any]) -> AsyncGenerator[tuple[str, Any], None]:
        generation_context = context.get("generation_context", {})

        try:
            outline_prompt = self.prompt_manager.render("chapter-outline", generation_context)
            outline_response = await self.llm_client.chat(outline_prompt)
            outline = outline_response.strip()
            yield "outline", outline
        except Exception as e:
            yield "error", f"生成章纲失败: {str(e)}"
            return

        generation_context["chapter_outline"] = outline

        try:
            content_prompt = self.prompt_manager.render("chapter-content", generation_context)
            full_content = ""
            async for token in self.llm_client.chat_stream(content_prompt):
                full_content += token
                yield "token", token
            yield "content_complete", full_content
        except Exception as e:
            yield "error", f"生成正文失败: {str(e)}"
            return
