import json

from domain.structure.storyline import Storyline, StorylineNode
from infrastructure.persistence.database import Database


class StorylineRepository:
    """故事线仓储 - DAG 结构持久化"""

    def __init__(self, db: Database):
        self.db = db

    def list_storylines(self, novel_id: str) -> list[Storyline]:
        rows = self.db.query(
            "SELECT * FROM storylines WHERE novel_id = ? ORDER BY sort_order",
            (novel_id,),
        )
        return [self._row_to_storyline(r) for r in rows]

    def get_storyline(self, storyline_id: str) -> Storyline | None:
        row = self.db.query_one(
            "SELECT * FROM storylines WHERE id = ?",
            (storyline_id,),
        )
        return self._row_to_storyline(row) if row else None

    def create_storyline(self, storyline: Storyline) -> Storyline:
        self.db.execute(
            """INSERT INTO storylines
               (id, novel_id, name, description, color, node_count, is_active, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                storyline.id,
                storyline.novel_id,
                storyline.name,
                storyline.description,
                storyline.color,
                storyline.node_count,
                1 if storyline.is_active else 0,
                storyline.order,
            ),
        )
        return storyline

    def update_storyline(self, storyline_id: str, data: dict) -> Storyline | None:
        storyline = self.get_storyline(storyline_id)
        if not storyline:
            return None
        for key, value in data.items():
            if hasattr(storyline, key):
                setattr(storyline, key, value)
        storyline.updated_at = Storyline.timestamps()

        self.db.execute(
            """UPDATE storylines SET name = ?, description = ?, color = ?,
               node_count = ?, is_active = ?, sort_order = ?, updated_at = ?
               WHERE id = ?""",
            (
                storyline.name,
                storyline.description,
                storyline.color,
                storyline.node_count,
                1 if storyline.is_active else 0,
                storyline.order,
                storyline.updated_at,
                storyline_id,
            ),
        )
        return storyline

    def delete_storyline(self, storyline_id: str) -> bool:
        self.db.execute("DELETE FROM storyline_nodes WHERE storyline_id = ?", (storyline_id,))
        self.db.execute("DELETE FROM storylines WHERE id = ?", (storyline_id,))
        return True

    def list_nodes(self, storyline_id: str) -> list[StorylineNode]:
        rows = self.db.query(
            "SELECT * FROM storyline_nodes WHERE storyline_id = ? ORDER BY y, x",
            (storyline_id,),
        )
        return [self._row_to_node(r) for r in rows]

    def list_nodes_by_novel(self, novel_id: str) -> list[StorylineNode]:
        rows = self.db.query(
            "SELECT * FROM storyline_nodes WHERE novel_id = ? ORDER BY storyline_id, y, x",
            (novel_id,),
        )
        return [self._row_to_node(r) for r in rows]

    def get_node(self, node_id: str) -> StorylineNode | None:
        row = self.db.query_one(
            "SELECT * FROM storyline_nodes WHERE id = ?",
            (node_id,),
        )
        return self._row_to_node(row) if row else None

    def create_node(self, node: StorylineNode) -> StorylineNode:
        self.db.execute(
            """INSERT INTO storyline_nodes
               (id, novel_id, storyline_id, title, description, node_type, status,
                chapter_index, chapter_id, x, y, width, height,
                parent_ids, child_ids, tags, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.id,
                node.novel_id,
                node.storyline_id,
                node.title,
                node.description,
                node.node_type,
                node.status,
                node.chapter_index,
                node.chapter_id,
                node.x,
                node.y,
                node.width,
                node.height,
                json.dumps(node.parent_ids, ensure_ascii=False),
                json.dumps(node.child_ids, ensure_ascii=False),
                json.dumps(node.tags, ensure_ascii=False),
                json.dumps(node.metadata, ensure_ascii=False),
            ),
        )
        self._update_node_count(node.storyline_id)
        return node

    def update_node(self, node_id: str, data: dict) -> StorylineNode | None:
        node = self.get_node(node_id)
        if not node:
            return None
        for key, value in data.items():
            if hasattr(node, key):
                setattr(node, key, value)
        node.updated_at = StorylineNode.timestamps()

        self.db.execute(
            """UPDATE storyline_nodes SET title = ?, description = ?, node_type = ?,
               status = ?, chapter_index = ?, chapter_id = ?,
               x = ?, y = ?, width = ?, height = ?,
               parent_ids = ?, child_ids = ?, tags = ?, metadata = ?, updated_at = ?
               WHERE id = ?""",
            (
                node.title,
                node.description,
                node.node_type,
                node.status,
                node.chapter_index,
                node.chapter_id,
                node.x,
                node.y,
                node.width,
                node.height,
                json.dumps(node.parent_ids, ensure_ascii=False),
                json.dumps(node.child_ids, ensure_ascii=False),
                json.dumps(node.tags, ensure_ascii=False),
                json.dumps(node.metadata, ensure_ascii=False),
                node.updated_at,
                node_id,
            ),
        )
        return node

    def delete_node(self, node_id: str) -> bool:
        node = self.get_node(node_id)
        if not node:
            return False

        storyline_id = node.storyline_id

        for pid in node.parent_ids:
            parent = self.get_node(pid)
            if parent and node_id in parent.child_ids:
                parent.child_ids.remove(node_id)
                self.update_node(pid, {"child_ids": parent.child_ids})

        for cid in node.child_ids:
            child = self.get_node(cid)
            if child and node_id in child.parent_ids:
                child.parent_ids.remove(node_id)
                self.update_node(cid, {"parent_ids": child.parent_ids})

        self.db.execute("DELETE FROM storyline_nodes WHERE id = ?", (node_id,))
        self._update_node_count(storyline_id)
        return True

    def connect_nodes(self, source_id: str, target_id: str) -> bool:
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        if not source or not target:
            return False

        if target_id not in source.child_ids:
            source.child_ids.append(target_id)
        if source_id not in target.parent_ids:
            target.parent_ids.append(source_id)

        self.update_node(source_id, {"child_ids": source.child_ids})
        self.update_node(target_id, {"parent_ids": target.parent_ids})
        return True

    def disconnect_nodes(self, source_id: str, target_id: str) -> bool:
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        if not source or not target:
            return False

        if target_id in source.child_ids:
            source.child_ids.remove(target_id)
        if source_id in target.parent_ids:
            target.parent_ids.remove(source_id)

        self.update_node(source_id, {"child_ids": source.child_ids})
        self.update_node(target_id, {"parent_ids": target.parent_ids})
        return True

    def _update_node_count(self, storyline_id: str):
        count = self.db.query_one(
            "SELECT COUNT(*) as cnt FROM storyline_nodes WHERE storyline_id = ?",
            (storyline_id,),
        )
        if count:
            self.db.execute(
                "UPDATE storylines SET node_count = ? WHERE id = ?",
                (count["cnt"], storyline_id),
            )

    def _row_to_storyline(self, row: dict) -> Storyline:
        return Storyline(
            id=row["id"],
            novel_id=row["novel_id"],
            name=row["name"],
            description=row["description"] or "",
            color=row["color"] or "#2080f0",
            node_count=row["node_count"] or 0,
            is_active=bool(row["is_active"]),
            order=row["sort_order"] or 0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_node(self, row: dict) -> StorylineNode:
        return StorylineNode(
            id=row["id"],
            novel_id=row["novel_id"],
            storyline_id=row["storyline_id"],
            title=row["title"],
            description=row["description"] or "",
            node_type=row["node_type"] or "scene",
            status=row["status"] or "draft",
            chapter_index=row["chapter_index"],
            chapter_id=row["chapter_id"],
            x=row["x"] or 0,
            y=row["y"] or 0,
            width=row["width"] or 180,
            height=row["height"] or 80,
            parent_ids=json.loads(row["parent_ids"]) if row["parent_ids"] else [],
            child_ids=json.loads(row["child_ids"]) if row["child_ids"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
