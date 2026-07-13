from domain.review_task import ReviewTask
from domain.shared.exceptions import ReviewTaskNotFoundException, ValidationException
from infrastructure.persistence.review_task_repo import ReviewTaskRepository


class ReviewTaskService:
    def __init__(self, review_task_repo: ReviewTaskRepository):
        self.review_task_repo = review_task_repo

    def list_tasks(self, page: int = 1, page_size: int = 20) -> dict:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        tasks, total = self.review_task_repo.list(page, page_size)
        return {
            "items": [_task_to_dict(task) for task in tasks],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create_task(self, title: str, novel_id: str | None = None) -> dict:
        title = title.strip()
        if not title:
            raise ValidationException("审查任务标题不能为空")
        task = ReviewTask(title=title, novel_id=novel_id)
        self.review_task_repo.create(task)
        return _task_to_dict(task)

    def get_task(self, task_id: str) -> dict:
        task = self.review_task_repo.get_by_id(task_id)
        if not task:
            raise ReviewTaskNotFoundException()
        return _task_to_dict(task)

    def update_task(self, task_id: str, status: str | None = None, result: str | None = None) -> dict:
        task = self.review_task_repo.get_by_id(task_id)
        if not task:
            raise ReviewTaskNotFoundException()

        if status is not None:
            task.status = status.strip()
        if result is not None:
            task.result = result
        task.updated_at = task.now()
        self.review_task_repo.update(task)
        return _task_to_dict(task)

    def delete_task(self, task_id: str) -> bool:
        return self.review_task_repo.delete(task_id)


def _task_to_dict(task: ReviewTask) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "novel_id": task.novel_id,
        "status": task.status,
        "result": task.result,
        "created_at": task.created_at.isoformat() if task.created_at else "",
        "updated_at": task.updated_at.isoformat() if task.updated_at else "",
    }
