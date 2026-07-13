import uuid
from datetime import datetime

from domain.world_setting import WorldSetting
from infrastructure.crypto import decrypt_api_key, encrypt_api_key
from infrastructure.persistence.database import Database

DEFAULT_SETTINGS = {
    # ---- AI / LLM 配置 ----
    "ai_provider": ("ollama", "AI提供商"),
    "default_model": ("", "默认模型"),
    "api_base_url": ("", "API基础地址"),
    "api_key": ("", "API密钥"),
    "temperature": ("0.7", "温度系数（创造性程度）"),
    "max_tokens": ("4096", "最大生成长度"),
    # ---- 生成配置 ----
    "target_words": ("2000", "每章目标字数"),
    "auto_review": ("true", "生成后是否自动审查"),
    "review_threshold": ("60", "审查通过分数线"),
    "max_retries": ("2", "LLM调用失败最大重试次数"),
    # ---- 界面配置 ----
    "language": ("zh-CN", "语言"),
    "theme": ("dark", "主题（dark/light）"),
}


class SettingRepository:
    def __init__(self, db: Database):
        self.db = db

    def list_by_novel(self, novel_id: str) -> list[WorldSetting]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM world_settings WHERE novel_id = ? ORDER BY setting_type, created_at", (novel_id,)
            ).fetchall()
            return [WorldSetting(**dict(row)) for row in rows]

    def get_by_id(self, setting_id: str) -> WorldSetting | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM world_settings WHERE id = ?", (setting_id,)).fetchone()
            return WorldSetting(**dict(row)) if row else None

    def create(self, setting: WorldSetting) -> WorldSetting:
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO world_settings (id, novel_id, name, setting_type, description,
                   parent_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    setting.id,
                    setting.novel_id,
                    setting.name,
                    setting.setting_type,
                    setting.description,
                    setting.parent_id,
                    setting.created_at,
                    setting.updated_at,
                ),
            )
        return setting

    def update(self, setting: WorldSetting) -> WorldSetting:
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE world_settings SET name = ?, setting_type = ?, description = ?,
                   parent_id = ?, updated_at = ? WHERE id = ?""",
                (
                    setting.name,
                    setting.setting_type,
                    setting.description,
                    setting.parent_id,
                    setting.updated_at,
                    setting.id,
                ),
            )
        return setting

    def delete(self, setting_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM world_settings WHERE id = ?", (setting_id,))
            return cursor.rowcount > 0

    def get_system_settings(self) -> dict:
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM system_settings").fetchall()
            return {row["key"]: row["value"] for row in rows}

    def update_system_setting(self, key: str, value: str, description: str = "") -> bool:
        # api_key 存储前加密
        if key == "api_key" and value:
            value = encrypt_api_key(value)
        with self.db.get_connection() as conn:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                """INSERT INTO system_settings (id, key, value, description, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                   description = excluded.description, updated_at = excluded.updated_at""",
                (str(uuid.uuid4()), key, value, description, now),
            )
            return cursor.rowcount > 0

    def init_default_settings(self) -> None:
        # H-02 修复：仅在键不存在时插入默认值，已存在的设置保留用户值。
        # 旧实现每次重启都调用 update_system_setting（UPSERT 覆盖），
        # 导致用户在前端配置的 LLM_API_KEY 等所有自定义项被重置为默认值。
        # 安全实践：默认值初始化必须使用 INSERT OR IGNORE，绝不覆盖现有数据。
        with self.db.get_connection() as conn:
            now = datetime.now().isoformat()
            for key, (default_value, description) in DEFAULT_SETTINGS.items():
                # api_key 默认值为空，加密后仍为空，无需特殊处理
                value = encrypt_api_key(default_value) if (key == "api_key" and default_value) else default_value
                conn.execute(
                    """INSERT OR IGNORE INTO system_settings (id, key, value, description, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), key, value, description, now),
                )

    def get_decrypted_api_key(self) -> str:
        """获取解密后的 API Key 明文（仅供 LLM 客户端初始化使用）。"""
        settings = self.get_system_settings()
        encrypted = settings.get("api_key", "")
        if not encrypted:
            return ""
        return decrypt_api_key(encrypted)
