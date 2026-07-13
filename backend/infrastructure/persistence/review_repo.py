import json

from domain.review import ReviewResult
from infrastructure.persistence.database import Database


class ReviewRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_by_chapter(self, chapter_id: str) -> ReviewResult | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM chapter_reviews WHERE chapter_id = ?", (chapter_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            data["red_line_violations"] = json.loads(data["red_line_violations"])
            data["dimension_scores"] = json.loads(data["dimension_scores"])
            return ReviewResult(**data)

    def create(self, review: ReviewResult) -> ReviewResult:
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO chapter_reviews (id, chapter_id, total_score, grade,
                   red_line_violations, dimension_scores, review_details, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    review.id,
                    review.chapter_id,
                    review.total_score,
                    review.grade,
                    json.dumps(review.red_line_violations, ensure_ascii=False),
                    json.dumps(review.dimension_scores, ensure_ascii=False),
                    review.review_details,
                    review.created_at,
                ),
            )
        return review

    def update(self, review: ReviewResult) -> ReviewResult:
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE chapter_reviews SET total_score = ?, grade = ?, red_line_violations = ?,
                   dimension_scores = ?, review_details = ? WHERE id = ?""",
                (
                    review.total_score,
                    review.grade,
                    json.dumps(review.red_line_violations, ensure_ascii=False),
                    json.dumps(review.dimension_scores, ensure_ascii=False),
                    review.review_details,
                    review.id,
                ),
            )
        return review

    def upsert(self, review: ReviewResult) -> ReviewResult:
        # 按 chapter_id 判断是否已存在审查记录：存在则复用其主键 id 调用 update，不存在则调用 create
        existing = self.get_by_chapter(review.chapter_id)
        if existing:
            review.id = existing.id
            return self.update(review)
        return self.create(review)
