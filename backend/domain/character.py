from dataclasses import dataclass

from .shared.base import BaseEntity


@dataclass
class Character(BaseEntity):
    novel_id: str = ""
    name: str = ""
    role: str = "配角"
    description: str = ""
    personality: str = ""
    appearance: str = ""
    background: str = ""
    gender: str = ""  # 性别（推荐值：男/女/其他/未设定）
    age: str = ""     # 年龄（字符串以支持灵活描述："25岁"/"约500岁"/"未知"）
