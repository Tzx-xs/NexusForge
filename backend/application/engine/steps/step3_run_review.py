from dataclasses import asdict
from typing import Any

from infrastructure.tools.red_line_checker import RedLineChecker
from infrastructure.tools.score_calculator import ScoreCalculator
from infrastructure.tools.text_cleaner import TextCleaner
from infrastructure.tools.word_counter import WordCounter

from .base_step import BaseStep


class Step3RunReview(BaseStep):
    name = "run_review"
    description = "质量审查"

    def __init__(self, llm_client=None, prompt_manager=None, context_builder=None, chapter_repo=None, review_repo=None):
        super().__init__(llm_client, prompt_manager, context_builder, chapter_repo, review_repo)
        self.red_line_checker = RedLineChecker()
        self.score_calculator = ScoreCalculator()
        self.text_cleaner = TextCleaner()
        self.word_counter = WordCounter()

    async def execute(self, chapter_id: str, context: dict[str, Any]) -> tuple[bool, dict[str, Any], str]:
        content = context.get("content", "")
        chapter = self.chapter_repo.get_by_id(chapter_id)

        if not chapter:
            return False, {}, "章节不存在"

        if not content:
            return False, {}, "无正文内容可审查"

        try:
            clean_content = self.text_cleaner.clean(content)

            red_line_violations = self.red_line_checker.check(clean_content)
            violation_dicts = [asdict(v) for v in red_line_violations]

            review_ctx = None
            if self.context_builder:
                review_ctx = self.context_builder.build_review_context(chapter_id, clean_content)

            if review_ctx:
                prompt_vars = self.context_builder.to_template_dict(review_ctx)
            else:
                prompt_vars = {
                    "chapter_title": chapter.title,
                    "chapter_content": clean_content,
                }

            review_prompt = self.prompt_manager.render("content-review", prompt_vars)

            llm_result = await self.llm_client.chat_json(review_prompt)

            quality_score = self.score_calculator.calculate(llm_result, red_line_violations)

            stats = self.word_counter.get_stats(clean_content)

            review_result = {
                "total_score": quality_score.total_score,
                "grade": quality_score.grade,
                "red_line_violations": violation_dicts,
                "dimension_scores": quality_score.dimension_scores,
                "review_details": {
                    "overall_comment": quality_score.overall_comment,
                    "issues": quality_score.issues,
                    "suggestions": quality_score.suggestions,
                    "stats": asdict(stats),
                },
            }
        except Exception as e:
            return False, {}, f"质量审查失败: {str(e)}"

        return True, {"review_result": review_result}, ""
