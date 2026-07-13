"""提示词注册表 — 扫描 prompt_packages/nodes/ 目录，注册并支持覆写。

节点目录结构：
    prompt_packages/nodes/{node_id}/
        package.yaml   — 元信息（id/name/category/variables/output_format/...）
        system.md      — system prompt 模板（含 {{var}} 占位）
        user.md        — user prompt 模板（含 {{var}} 占位）
        extras.json    — 可选附加配置

覆写语义：
- 扫描时按 sort_order 升序加载（sort_order 小的先注册，大的后注册覆盖）
- 同名节点（id 相同）后注册覆盖先注册
- StellarScribe 默认节点 sort_order=5，PlotPilot 节点 sort_order=10+，
  故 PlotPilot 节点会覆盖 StellarScribe 同名节点（如有）；
  但 StellarScribe 独有节点（chapter-content/chapter-outline/content-review）
  因 PlotPilot 无同名节点，最终保留 StellarScribe 版本。

与 PromptManager 兼容：
- PromptRegistry.get_node(name) 返回 PromptNode 对象（含 system/user/variables）
- PromptRegistry.format_prompt(name, **kwargs) 返回 (system, user) tuple
- 旧 PromptManager 调用可逐步迁移到 PromptRegistry
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_PACKAGES_DIR = Path(__file__).parent / "prompt_packages" / "nodes"

# 变量占位正则：{{var_name}}
_VAR_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class PromptRegistryError(Exception):
    """提示词注册表错误。"""


@dataclass
class PromptVariable:
    """提示词变量定义。"""
    name: str
    desc: str = ""
    type: str = "string"
    required: bool = False
    default: Any = None


@dataclass
class PromptNode:
    """提示词节点（注册后的完整对象）。"""
    id: str
    name: str = ""
    category: str = ""
    source: str = ""
    description: str = ""
    builtin: bool = False
    tags: list[str] = field(default_factory=list)
    variables: list[PromptVariable] = field(default_factory=list)
    output_format: str = "text"
    estimated_tokens: int = 0
    sort_order: int = 100
    system_prompt: str = ""
    user_prompt: str = ""
    extras: dict[str, Any] = field(default_factory=dict)
    # 来源目录路径（调试用）
    source_dir: Path | None = None

    def to_dict(self, include_prompts: bool = True) -> dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "source": self.source,
            "description": self.description,
            "builtin": self.builtin,
            "tags": list(self.tags),
            "variables": [
                {
                    "name": v.name,
                    "desc": v.desc,
                    "type": v.type,
                    "required": v.required,
                    "default": v.default,
                }
                for v in self.variables
            ],
            "output_format": self.output_format,
            "estimated_tokens": self.estimated_tokens,
            "sort_order": self.sort_order,
        }
        if include_prompts:
            d["system_prompt"] = self.system_prompt
            d["user_prompt"] = self.user_prompt
        return d


class PromptRegistry:
    """提示词注册表，扫描目录并注册节点，支持覆写。"""

    def __init__(self, nodes_dir: Path | None = None):
        self.nodes_dir = nodes_dir or DEFAULT_PROMPT_PACKAGES_DIR
        # id -> PromptNode（注册后的最终结果）
        self._nodes: dict[str, PromptNode] = {}
        self._loaded: bool = False

    def _load_package_yaml(self, pkg_path: Path) -> dict[str, Any]:
        """加载 package.yaml。"""
        try:
            with pkg_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            raise PromptRegistryError(
                f"package.yaml 解析失败 {pkg_path}: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise PromptRegistryError(
                f"package.yaml 顶层必须是映射 {pkg_path}: {type(data).__name__}"
            )
        return data

    def _load_text(self, path: Path) -> str:
        """加载文本文件（system.md/user.md）。"""
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _load_extras(self, path: Path) -> dict[str, Any]:
        """加载 extras.json（可选）。"""
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("extras.json 加载失败 %s: %s", path, exc)
            return {}

    def _parse_variables(self, raw_vars: list | None) -> list[PromptVariable]:
        """解析变量定义列表。"""
        if not raw_vars:
            return []
        result: list[PromptVariable] = []
        for item in raw_vars:
            if not isinstance(item, dict):
                continue
            result.append(PromptVariable(
                name=str(item.get("name", "")),
                desc=str(item.get("desc", "")),
                type=str(item.get("type", "string")),
                required=bool(item.get("required", False)),
                default=item.get("default"),
            ))
        return result

    def _load_node(self, node_dir: Path) -> PromptNode:
        """加载单个节点目录。"""
        pkg_path = node_dir / "package.yaml"
        if not pkg_path.exists():
            raise PromptRegistryError(f"节点缺少 package.yaml: {node_dir}")
        data = self._load_package_yaml(pkg_path)
        node_id = str(data.get("id", node_dir.name))
        system = self._load_text(node_dir / "system.md")
        user = self._load_text(node_dir / "user.md")
        extras = self._load_extras(node_dir / "extras.json")
        variables = self._parse_variables(data.get("variables"))
        return PromptNode(
            id=node_id,
            name=str(data.get("name", node_id)),
            category=str(data.get("category", "")),
            source=str(data.get("source", "")),
            description=str(data.get("description", "")),
            builtin=bool(data.get("builtin", False)),
            tags=list(data.get("tags") or []),
            variables=variables,
            output_format=str(data.get("output_format", "text")),
            estimated_tokens=int(data.get("estimated_tokens", 0) or 0),
            sort_order=int(data.get("sort_order", 100) or 100),
            system_prompt=system,
            user_prompt=user,
            extras=extras,
            source_dir=node_dir,
        )

    def load_all(self, force: bool = False) -> None:
        """扫描 nodes_dir 加载所有节点。

        按 sort_order 升序加载，后加载的同名节点覆盖先加载的（覆写语义）。
        force=True 强制重新加载（清空已注册节点）。
        """
        if self._loaded and not force:
            return
        if force:
            self._nodes.clear()
        if not self.nodes_dir.exists():
            logger.warning("提示词节点目录不存在: %s", self.nodes_dir)
            self._loaded = True
            return
        # 收集所有节点目录
        node_dirs = [d for d in self.nodes_dir.iterdir() if d.is_dir()]
        # 按 sort_order 升序加载（小的先注册，大的后注册覆盖）
        loaded: list[PromptNode] = []
        for d in node_dirs:
            try:
                node = self._load_node(d)
                loaded.append(node)
            except PromptRegistryError as exc:
                logger.warning("跳过提示词节点 %s: %s", d, exc)
        loaded.sort(key=lambda n: n.sort_order)
        for node in loaded:
            self._nodes[node.id] = node
            logger.debug("已注册提示词节点: %s (source=%s, sort_order=%d)", node.id, node.source, node.sort_order)
        self._loaded = True
        logger.info("提示词注册表加载完成: %d 个节点", len(self._nodes))

    def register(self, node: PromptNode) -> None:
        """手动注册单个节点（覆盖同名）。"""
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> PromptNode:
        """获取节点（不存在抛错）。"""
        self.load_all()
        if node_id not in self._nodes:
            raise PromptRegistryError(f"提示词节点不存在: {node_id}")
        return self._nodes[node_id]

    def has_node(self, node_id: str) -> bool:
        """判断节点是否存在。"""
        self.load_all()
        return node_id in self._nodes

    def list_nodes(self, category: str | None = None) -> list[PromptNode]:
        """列出所有节点（可按 category 过滤）。"""
        self.load_all()
        nodes = list(self._nodes.values())
        if category:
            nodes = [n for n in nodes if n.category == category]
        return sorted(nodes, key=lambda n: (n.category, n.sort_order, n.id))

    def _render(self, template: str, variables: dict[str, Any]) -> tuple[str, list[str]]:
        """渲染模板，返回 (渲染后文本, 缺失变量列表)。"""
        missing: list[str] = []

        def replacer(match: re.Match[str]) -> str:
            key = match.group(1)
            if key in variables:
                return str(variables[key])
            # 未提供：记录缺失，保留占位
            missing.append(key)
            return match.group(0)

        rendered = _VAR_PATTERN.sub(replacer, template)
        return rendered, missing

    def format_prompt(
        self,
        node_id: str,
        variables: dict[str, Any] | None = None,
        strict: bool = False,
    ) -> tuple[str, str]:
        """渲染指定节点的 system/user prompt。

        variables: 变量值字典
        strict: True 时缺失必填变量抛错；False 时仅记录但不抛错（保留占位）
        返回 (system_prompt, user_prompt)
        """
        node = self.get_node(node_id)
        variables = variables or {}
        # 应用默认值
        for var in node.variables:
            if var.name not in variables and var.default is not None:
                variables[var.name] = var.default
        system, sys_missing = self._render(node.system_prompt, variables)
        user, user_missing = self._render(node.user_prompt, variables)
        all_missing = sys_missing + user_missing
        if strict and all_missing:
            # 检查是否为必填变量
            required_names = {v.name for v in node.variables if v.required}
            missing_required = [m for m in all_missing if m in required_names]
            if missing_required:
                raise PromptRegistryError(
                    f"节点 {node_id} 缺失必填变量: {', '.join(sorted(set(missing_required)))}"
                )
        return system, user


# ─── 模块级单例 + 便捷函数 ─────────────────────────────────────────────────

_default_registry: PromptRegistry | None = None


def get_default_registry() -> PromptRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = PromptRegistry()
    return _default_registry


@lru_cache(maxsize=64)
def format_prompt_cached(node_id: str, **variables) -> tuple[str, str]:
    """便捷函数：用默认注册表渲染 prompt（带 LRU 缓存）。

    注意：variables 必须是可哈希的（str/int/float/bool/tuple）。
    """
    return get_default_registry().format_prompt(node_id, dict(variables))


def list_prompt_nodes(category: str | None = None) -> list[PromptNode]:
    """便捷函数：列出所有提示词节点。"""
    return get_default_registry().list_nodes(category=category)
