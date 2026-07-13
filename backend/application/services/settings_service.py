from __future__ import annotations

from infrastructure.persistence.setting_repo import DEFAULT_SETTINGS, SettingRepository


class SettingsService:
    """系统设置服务 — 管理数据库中的用户可配置业务设置"""

    def __init__(self, setting_repo: SettingRepository):
        self.setting_repo = setting_repo

    # ---- 计划书接口 ----

    def get_all(self) -> dict:
        """获取所有设置（合并默认值）"""
        db_settings = self.setting_repo.get_system_settings()
        result = {}
        for key, (default_value, _description) in DEFAULT_SETTINGS.items():
            result[key] = db_settings.get(key, default_value)
        return result

    def get(self, key: str) -> str | None:
        """获取单个设置（不存在返回 None）"""
        db_settings: dict[str, str] = self.setting_repo.get_system_settings()
        if key in db_settings:
            return db_settings[key]
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key][0]
        return None

    def update(self, key: str, value: str) -> None:
        """更新单个设置"""
        description = DEFAULT_SETTINGS.get(key, ("", ""))[1]
        self.setting_repo.update_system_setting(key, str(value), description)

    def batch_update(self, updates: dict) -> None:
        """批量更新设置"""
        for key, value in updates.items():
            description = DEFAULT_SETTINGS.get(key, ("", ""))[1]
            self.setting_repo.update_system_setting(key, str(value), description)

    def reset_to_defaults(self) -> None:
        """重置为默认值"""
        for key, (default_value, description) in DEFAULT_SETTINGS.items():
            self.setting_repo.update_system_setting(key, default_value, description)

    # ---- 向后兼容接口 ----

    def get_all_settings(self) -> dict:
        return self.get_all()

    def update_settings(self, settings: dict) -> dict:
        self.batch_update(settings)
        return self.get_all()

    def get_setting(self, key: str, default: str = "") -> str:
        val = self.get(key)
        return val if val is not None else default
