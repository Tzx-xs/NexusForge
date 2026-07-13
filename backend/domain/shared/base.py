from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from uuid import uuid4


def _parse_datetime(value: str | datetime | None) -> datetime:
    """将 str / datetime / None 转换为 datetime。

    SQLite 读取时返回字符串，本函数保证 BaseEntity 内部始终持有 datetime。
    """
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # 兼容 SQLite 默认格式 "YYYY-MM-DD HH:MM:SS.ffffff+00:00"
            # Python 3.11+ 的 fromisoformat 支持带时区，但旧格式可能需替换
            return datetime.fromisoformat(value.replace(" ", "T"))
        except ValueError:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.now(UTC)
    return datetime.now(UTC)


@dataclass
class BaseEntity:
    """领域对象基类。

    时间戳类型为 datetime（Phase 3.3 改进）：
        - 内部统一持有 datetime 对象
        - __post_init__ 自动处理 SQLite 读取返回的 str
        - to_dict() 输出 ISO 字符串，保持 API JSON 兼容
        - Repository 写入时调用 .isoformat() 序列化
    """

    id: str = field(default_factory=lambda: BaseEntity.generate_id())
    created_at: datetime = field(default_factory=lambda: BaseEntity.now())
    updated_at: datetime = field(default_factory=lambda: BaseEntity.now())

    def __post_init__(self) -> None:
        """保证时间戳字段始终为 datetime（向后兼容 str 输入）。"""
        # 直接 __dict__ 赋值，避免触发 dataclasses 的 __setattr__ 限制
        object.__setattr__(self, "created_at", _parse_datetime(self.created_at))
        object.__setattr__(self, "updated_at", _parse_datetime(self.updated_at))

    @staticmethod
    def generate_id() -> str:
        return uuid4().hex

    @staticmethod
    def now() -> datetime:
        """返回当前 UTC datetime（推荐使用）。"""
        return datetime.now(UTC)

    @staticmethod
    def timestamps() -> datetime:
        """返回当前 UTC datetime（兼容旧调用）。

        Phase 3.3 前返回 ISO 字符串，现在返回 datetime。
        调用方如 `entity.updated_at = Entity.timestamps()` 会自动得到 datetime。
        """
        return datetime.now(UTC)

    def to_dict(self) -> dict:
        """序列化为字典，datetime 字段输出 ISO 字符串。"""
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, datetime):
                result[f.name] = value.isoformat()
            else:
                result[f.name] = value
        return result

    def to_db_dict(self) -> dict:
        """序列化为数据库写入格式（datetime → ISO 字符串）。

        Repository 在执行 INSERT/UPDATE 时应使用本方法，
        保证 SQLite 存储格式统一且可被 fromisoformat 解析。
        """
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, datetime):
                result[f.name] = value.isoformat()
            else:
                result[f.name] = value
        return result
