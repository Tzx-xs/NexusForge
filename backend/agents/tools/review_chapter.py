from __future__ import annotations

from typing import Any

from application.services.review_service import ReviewService

from .base import Tool, ToolResult


class ReviewChapterTool(Tool):
    name = "review_chapter"
    description = "对指定章节进行内容审查，返回评分、等级、红线违规及维度分数等审查报告摘要。"

    def __init__(self, review_service: ReviewService):
        self.review_service = review_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "待审查章节ID"},
            },
            "required": ["chapter_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            chapter_id = kwargs["chapter_id"]
            review = await self.review_service.review_chapter(chapter_id)
            if review is None:
                return ToolResult(success=False, error="审查失败：service 返回 None")

            violations = review.red_line_violations or []
            total_issues = len(violations) if isinstance(violations, list) else 0
            grade = (review.grade or "").upper()
            passed = grade in {"S", "A", "B"} or review.total_score >= 70

            return ToolResult(
                success=True,
                data={
                    "review_id": review.id,
                    "chapter_id": review.chapter_id,
                    "overall_score": review.total_score,
                    "grade": review.grade,
                    "total_issues": total_issues,
                    "passed": passed,
                    "dimension_scores": review.dimension_scores or {},
                    "red_line_violations": violations,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
