from typing import Any

from .base_step import BaseStep


class Step1BuildContext(BaseStep):
    name = "build_context"
    description = "构建生成上下文"

    async def execute(self, chapter_id: str, context: dict[str, Any]) -> tuple[bool, dict[str, Any], str]:
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not chapter:
            return False, {}, "章节不存在"

        novel_id = chapter.novel_id
        generation_context = self.context_builder.build_generation_context(novel_id, chapter_id)

        if not generation_context.get("novel_title"):
            return False, {}, "小说数据缺失，无法构建上下文"

        result = {
            "generation_context": generation_context,
            "novel_id": novel_id,
            "chapter_id": chapter_id,
        }
        return True, result, ""
