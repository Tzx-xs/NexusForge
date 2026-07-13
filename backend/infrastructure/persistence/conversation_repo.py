from __future__ import annotations

import time
import uuid

from domain.agent import Conversation, Message
from infrastructure.persistence.database import Database


class ConversationRepository:
    def __init__(self, db: Database):
        self.db = db

    def create_conversation(self, novel_id: str | None = None, title: str = "") -> Conversation:
        """创建新会话，返回完整对象"""
        conv_id = str(uuid.uuid4())[:12]
        now = time.time()
        conv = Conversation(id=conv_id, novel_id=novel_id, title=title, created_at=now, updated_at=now)
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO conversations (id, novel_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conv.id, conv.novel_id, conv.title, conv.created_at, conv.updated_at),
            )
            conn.commit()
        return conv

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT id, novel_id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        return self._row_to_conversation(row) if row else None

    def list_conversations(self, novel_id: str | None = None, limit: int = 50) -> list[Conversation]:
        if novel_id:
            rows = (
                self.db.get_connection()
                .execute(
                    "SELECT id, novel_id, title, created_at, updated_at FROM conversations WHERE novel_id = ? ORDER BY updated_at DESC LIMIT ?",
                    (novel_id, limit),
                )
                .fetchall()
            )
        else:
            rows = (
                self.db.get_connection()
                .execute(
                    "SELECT id, novel_id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                )
                .fetchall()
            )
        return [self._row_to_conversation(r) for r in rows]

    def delete_conversation(self, conversation_id: str) -> bool:
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
            return cur.rowcount > 0

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: str | None = None,
        tool_name: str | None = None,
    ) -> Message:
        msg_id = str(uuid.uuid4())[:12]
        now = time.time()
        msg = Message(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_name=tool_name,
            created_at=now,
        )
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, tool_calls, tool_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (msg.id, msg.conversation_id, msg.role, msg.content, msg.tool_calls, msg.tool_name, msg.created_at),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            conn.commit()
        return msg

    def list_messages(self, conversation_id: str, limit: int = 100) -> list[Message]:
        rows = (
            self.db.get_connection()
            .execute(
                "SELECT id, conversation_id, role, content, tool_calls, tool_name, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
                (conversation_id, limit),
            )
            .fetchall()
        )
        return [self._row_to_message(r) for r in rows]

    def _row_to_conversation(self, row) -> Conversation:
        return Conversation(
            id=row[0],
            novel_id=row[1],
            title=row[2],
            created_at=row[3],
            updated_at=row[4],
        )

    def _row_to_message(self, row) -> Message:
        return Message(
            id=row[0],
            conversation_id=row[1],
            role=row[2],
            content=row[3],
            tool_calls=row[4],
            tool_name=row[5],
            created_at=row[6],
        )
