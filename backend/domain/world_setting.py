from dataclasses import dataclass

from .shared.base import BaseEntity


@dataclass
class WorldSetting(BaseEntity):
    novel_id: str = ""
    name: str = ""
    setting_type: str = "other"
    description: str = ""
    parent_id: str | None = None
