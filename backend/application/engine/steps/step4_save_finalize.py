import logging
from typing import Any

from .base_step import BaseStep

logger = logging.getLogger(__name__)


class Step4SaveFinalize(BaseStep):
    name = "save_finalize"
    description = "保存并收尾"

    async def execute(self, chapter_id: str, context: dict[str, Any]) -> tuple[bool, dict[str, Any], str]:
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not chapter:
            return False, {}, "章节不存在"

        content = context.get("content", "")
        outline = context.get("outline", "")
        review_result = context.get("review_result", {})
        word_count = context.get("word_count", len(content))

        try:
            chapter.outline = outline
            chapter.content = content
            chapter.word_count = word_count
            # Sprint 1：删除 "generated" 死状态，由 ChapterService 或 FinalizeStep 设最终态
            self.chapter_repo.update(chapter)
        except Exception as e:
            return False, {}, f"保存章节失败: {str(e)}"

        try:
            if review_result:
                from domain.review import ReviewResult

                review = ReviewResult(
                    chapter_id=chapter_id,
                    total_score=review_result.get("total_score", 0.0),
                    grade=review_result.get("grade", "C"),
                    red_line_violations=review_result.get("red_line_violations", []),
                    dimension_scores=review_result.get("dimension_scores", {}),
                    review_details=review_result.get("review_details", ""),
                )
                self.review_repo.upsert(review)
        except Exception:
            logger.warning("Review upsert failed", exc_info=True)

        result = {
            "chapter_id": chapter_id,
            "word_count": word_count,
            "score": review_result.get("total_score", 0.0),
        }
        return True, result, ""
