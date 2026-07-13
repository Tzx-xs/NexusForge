"""题材包加载器 — 支持继承（extends）与混入（mixins）合并。

题材包 YAML 结构：
    name: 题材名
    extends: base              # 可选，继承自 base（多级继承支持）
    mixins: [anti_guidelines]  # 可选，混入其他包的特定字段
    writing_rules: [...]       # 写作规则
    anti_guidelines: [...]     # 反套路约束
    motifs: [...]              # 核心母题
    rules: [...]               # 通用规则（与 writing_rules 同义，保留兼容）

合并语义：
- extends：父包字段先入，子包字段覆盖（标量）或追加（列表）
- mixins：将指定包的特定列表字段追加到当前包（不覆盖）
- 列表字段（writing_rules/anti_guidelines/motifs/rules）追加合并
- 标量字段（name）子包覆盖父包
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# 题材包目录（默认 backend/config/genre_packs）
DEFAULT_GENRE_PACKS_DIR = Path(__file__).parent / "genre_packs"

# 列表字段（追加合并）；其余字段视为标量（覆盖）
_LIST_FIELDS: frozenset[str] = frozenset({
    "writing_rules", "anti_guidelines", "motifs", "rules", "mixins",
})


class GenrePackError(Exception):
    """题材包加载/合并错误。"""


@dataclass
class GenrePack:
    """题材包数据（合并后的最终结果）。"""
    name: str = ""
    extends: str | None = None
    mixins: list[str] = field(default_factory=list)
    writing_rules: list[str] = field(default_factory=list)
    anti_guidelines: list[str] = field(default_factory=list)
    motifs: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    # 原始字段（未合并前），便于调试
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "extends": self.extends,
            "mixins": list(self.mixins),
            "writing_rules": list(self.writing_rules),
            "anti_guidelines": list(self.anti_guidelines),
            "motifs": list(self.motifs),
            "rules": list(self.rules),
        }


class GenrePackLoader:
    """题材包加载器，支持 extends 继承与 mixins 混入。"""

    def __init__(self, packs_dir: Path | None = None):
        self.packs_dir = packs_dir or DEFAULT_GENRE_PACKS_DIR
        # 缓存：pack_name -> 原始 yaml dict（未合并）
        self._raw_cache: dict[str, dict[str, Any]] = {}

    def _load_raw(self, pack_name: str) -> dict[str, Any]:
        """加载单个题材包的原始 YAML（带缓存）。"""
        if pack_name in self._raw_cache:
            return self._raw_cache[pack_name]
        path = self.packs_dir / f"{pack_name}.yaml"
        if not path.exists():
            raise GenrePackError(f"题材包不存在: {pack_name} (路径: {path})")
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            raise GenrePackError(f"题材包 YAML 解析失败 {pack_name}: {exc}") from exc
        if not isinstance(data, dict):
            raise GenrePackError(f"题材包 {pack_name} 顶层必须是映射，实际: {type(data).__name__}")
        self._raw_cache[pack_name] = data
        return data

    def _merge_list_field(
        self,
        parent_value: list[Any] | None,
        child_value: list[Any] | None,
    ) -> list[Any]:
        """列表字段合并：父先入，子追加（去重保序）。"""
        merged: list[Any] = []
        seen: set[str] = set()
        for item in (parent_value or []) + (child_value or []):
            # 仅对字符串去重；非字符串一律保留
            if isinstance(item, str):
                if item in seen:
                    continue
                seen.add(item)
            merged.append(item)
        return merged

    def _resolve(self, pack_name: str, _chain: set[str] | None = None) -> dict[str, Any]:
        """递归解析题材包（含 extends 继承 + mixins 混入）。

        _chain 用于循环继承检测。
        """
        chain = _chain or set()
        if pack_name in chain:
            raise GenrePackError(f"检测到题材包循环继承: {' -> '.join(chain)} -> {pack_name}")
        chain = chain | {pack_name}

        raw = self._load_raw(pack_name)
        extends = raw.get("extends")
        mixins = raw.get("mixins") or []

        # 基准：继承父包的合并结果
        if extends:
            base = self._resolve(extends, chain)
            merged: dict[str, Any] = dict(base)
        else:
            merged = {}

        # 先合并 mixins（每个 mixin 是一个 pack_name，取其特定列表字段追加）
        for mixin_name in mixins:
            if mixin_name == pack_name:
                raise GenrePackError(f"题材包 {pack_name} 不能 mixins 自身")
            mixin_resolved = self._resolve(mixin_name, chain)
            for field_name in _LIST_FIELDS:
                if field_name == "mixins":
                    continue  # mixins 字段本身不合并
                if field_name in mixin_resolved:
                    merged[field_name] = self._merge_list_field(
                        merged.get(field_name),
                        mixin_resolved[field_name],
                    )

        # 最后合并当前包自身字段（覆盖/追加到已合并结果上）
        for key, value in raw.items():
            if key in ("extends", "mixins"):
                # extends/mixins 仅作为合并指令，不进入最终字段（除非显式保留）
                if key == "mixins":
                    merged["mixins"] = list(mixins)
                continue
            if key in _LIST_FIELDS:
                merged[key] = self._merge_list_field(merged.get(key), value)
            else:
                # 标量字段：子覆盖父
                merged[key] = value

        return merged

    def load(self, pack_name: str) -> GenrePack:
        """加载并合并题材包，返回 GenrePack 对象。"""
        merged = self._resolve(pack_name)
        raw = self._load_raw(pack_name)
        return GenrePack(
            name=merged.get("name", pack_name),
            extends=merged.get("extends"),
            mixins=list(merged.get("mixins") or []),
            writing_rules=list(merged.get("writing_rules") or []),
            anti_guidelines=list(merged.get("anti_guidelines") or []),
            motifs=list(merged.get("motifs") or []),
            rules=list(merged.get("rules") or []),
            raw=raw,
        )

    def list_packs(self) -> list[str]:
        """列出所有可用题材包名（不含扩展名）。"""
        if not self.packs_dir.exists():
            return []
        return sorted(
            p.stem for p in self.packs_dir.glob("*.yaml")
            if p.is_file()
        )


# ─── 模块级单例 + 便捷函数 ─────────────────────────────────────────────────

_default_loader: GenrePackLoader | None = None


def get_default_loader() -> GenrePackLoader:
    global _default_loader
    if _default_loader is None:
        _default_loader = GenrePackLoader()
    return _default_loader


@lru_cache(maxsize=32)
def load_genre_pack(pack_name: str) -> GenrePack:
    """便捷函数：用默认加载器加载题材包（带 LRU 缓存）。"""
    return get_default_loader().load(pack_name)


def list_genre_packs() -> list[str]:
    """便捷函数：列出所有可用题材包。"""
    return get_default_loader().list_packs()
