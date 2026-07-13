from __future__ import annotations

from domain.character import Character
from domain.shared.exceptions import (
    CharacterNotFoundException,
    SettingNotFoundException,
)
from domain.world_setting import WorldSetting
from infrastructure.persistence.character_repo import CharacterRepository
from infrastructure.persistence.setting_repo import SettingRepository


class BibleService:
    def __init__(self, character_repo: CharacterRepository, setting_repo: SettingRepository):
        self.character_repo = character_repo
        self.setting_repo = setting_repo

    def list_characters(self, novel_id: str) -> list[Character]:
        return self.character_repo.list_by_novel(novel_id)

    def create_character(self, novel_id: str, name: str, **kwargs) -> Character:
        character = Character(novel_id=novel_id, name=name, **kwargs)
        return self.character_repo.create(character)

    def update_character(self, character_id: str, **kwargs) -> Character:
        character = self.character_repo.get_by_id(character_id)
        if not character:
            raise CharacterNotFoundException()
        for key, value in kwargs.items():
            if hasattr(character, key):
                setattr(character, key, value)
        character.updated_at = Character.timestamps()
        return self.character_repo.update(character)

    def delete_character(self, character_id: str) -> bool:
        return self.character_repo.delete(character_id)

    def list_settings(self, novel_id: str, setting_type: str | None = None) -> list[WorldSetting]:
        settings = self.setting_repo.list_by_novel(novel_id)
        if setting_type:
            settings = [s for s in settings if s.setting_type == setting_type]
        return settings

    def create_setting(self, novel_id: str, name: str, **kwargs) -> WorldSetting:
        setting = WorldSetting(novel_id=novel_id, name=name, **kwargs)
        return self.setting_repo.create(setting)

    def update_setting(self, setting_id: str, **kwargs) -> WorldSetting:
        setting = self.setting_repo.get_by_id(setting_id)
        if not setting:
            raise SettingNotFoundException()
        for key, value in kwargs.items():
            if hasattr(setting, key):
                setattr(setting, key, value)
        setting.updated_at = WorldSetting.timestamps()
        return self.setting_repo.update(setting)

    def delete_setting(self, setting_id: str) -> bool:
        return self.setting_repo.delete(setting_id)
