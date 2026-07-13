from __future__ import annotations

from dataclasses import asdict

from application.engine.prompt_manager import PromptManager
from domain.review import ReviewResult
from domain.shared.exceptions import ChapterNotFoundException
from infrastructure.ai.llm_client import LLMClient
from infrastructure.persistence.chapter_repo import ChapterRepository
from infrastructure.persistence.review_repo import ReviewRepository
from infrastructure.tools.red_line_checker import RedLineChecker
from infrastructure.tools.score_calculator import ScoreCalculator
from infrastructure.tools.text_cleaner import TextCleaner
from infrastructure.tools.word_counter import WordCounter


class ReviewService:
    def __init__(
        self,
        review_repo: ReviewRepository,
        chapter_repo: ChapterRepository,
        llm_client: LLMClient,
        prompt_manager: PromptManager,
    ):
        self.review_repo = review_repo
        self.chapter_repo = chapter_repo
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.red_line_checker = RedLineChecker()
        self.score_calculator = ScoreCalculator()
        self.text_cleaner = TextCleaner()
        self.word_counter = WordCounter()

    async def review_chapter(self, chapter_id: str) -> ReviewResult:
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not chapter:
            raise ChapterNotFoundException()

        clean_content = self.text_cleaner.clean(chapter.content)

        red_line_violations = self.red_line_checker.check(clean_content)
        violation_dicts = [asdict(v) for v in red_line_violations]

        prompt = self.prompt_manager.render(
            "content-review",
            {
                "chapter_title": chapter.title,
                "chapter_content": clean_content,
            },
        )

        llm_result = await self.llm_client.chat_json(prompt)

        quality_score = self.score_calculator.calculate(llm_result, red_line_violations)

        stats = self.word_counter.get_stats(clean_content)

        review_details = {
            "overall_comment": quality_score.overall_comment,
            "issues": quality_score.issues,
            "suggestions": quality_score.suggestions,
            "stats": asdict(stats),
        }

        existing = self.review_repo.get_by_chapter(chapter_id)
        if existing:
            existing.total_score = quality_score.total_score
            existing.grade = quality_score.grade
            existing.red_line_violations = violation_dicts
            existing.dimension_scores = quality_score.dimension_scores
            existing.review_details = str(review_details)
            return self.review_repo.update(existing)

        review = ReviewResult(
            chapter_id=chapter_id,
            total_score=quality_score.total_score,
            grade=quality_score.grade,
            red_line_violations=violation_dicts,
            dimension_scores=quality_score.dimension_scores,
            review_details=str(review_details),
        )
        return self.review_repo.create(review)

    def get_review(self, chapter_id: str) -> ReviewResult | None:
        return self.review_repo.get_by_chapter(chapter_id)
