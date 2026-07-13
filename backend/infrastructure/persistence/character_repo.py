from domain.character import Character
from infrastructure.persistence.database import Database


class CharacterRepository:
    def __init__(self, db: Database):
        self.db = db

    def list_by_novel(self, novel_id: str) -> list[Character]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM characters WHERE novel_id = ? ORDER BY created_at", (novel_id,)
            ).fetchall()
            return [Character(**dict(row)) for row in rows]

    def get_by_id(self, character_id: str) -> Character | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
            return Character(**dict(row)) if row else None

    def create(self, character: Character) -> Character:
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO characters (id, novel_id, name, role, description, personality,
                   appearance, background, gender, age, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    character.id,
                    character.novel_id,
                    character.name,
                    character.role,
                    character.description,
                    character.personality,
                    character.appearance,
                    character.background,
                    character.gender,
                    character.age,
                    character.created_at,
                    character.updated_at,
                ),
            )
        return character

    def update(self, character: Character) -> Character:
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE characters SET name = ?, role = ?, description = ?, personality = ?,
                   appearance = ?, background = ?, gender = ?, age = ?, updated_at = ? WHERE id = ?""",
                (
                    character.name,
                    character.role,
                    character.description,
                    character.personality,
                    character.appearance,
                    character.background,
                    character.gender,
                    character.age,
                    character.updated_at,
                    character.id,
                ),
            )
        return character

    def delete(self, character_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM characters WHERE id = ?", (character_id,))
            return cursor.rowcount > 0
