"""提示词注册表测试 — 验证扫描/注册/覆写/渲染。"""
from __future__ import annotations

from pathlib import Path

import pytest

from infrastructure.ai.prompt_registry import (
    DEFAULT_PROMPT_PACKAGES_DIR,
    PromptNode,
    PromptRegistry,
    PromptRegistryError,
    PromptVariable,
)


@pytest.fixture
def registry() -> PromptRegistry:
    return PromptRegistry(DEFAULT_PROMPT_PACKAGES_DIR)


class TestScanAndLoad:
    """扫描加载测试。"""

    def test_load_all_discovers_nodes(self, registry: PromptRegistry):
        registry.load_all()
        # PlotPilot 76 + StellarScribe 3 = 79 节点
        assert len(registry._nodes) >= 70

    def test_stellar_nodes_present(self, registry: PromptRegistry):
        """StellarScribe 默认节点应存在。"""
        registry.load_all()
        assert registry.has_node("chapter-content")
        assert registry.has_node("chapter-outline")
        assert registry.has_node("content-review")

    def test_plotpilot_nodes_present(self, registry: PromptRegistry):
        """PlotPilot 节点应存在。"""
        registry.load_all()
        assert registry.has_node("chapter-prose-generation")
        assert registry.has_node("planning-plot-outline")

    def test_list_nodes_returns_sorted(self, registry: PromptRegistry):
        nodes = registry.list_nodes()
        assert len(nodes) > 0
        # 应按 category + sort_order + id 排序
        for i in range(len(nodes) - 1):
            key_a = (nodes[i].category, nodes[i].sort_order, nodes[i].id)
            key_b = (nodes[i + 1].category, nodes[i + 1].sort_order, nodes[i + 1].id)
            assert key_a <= key_b


class TestStellarScribeNodes:
    """StellarScribe 默认节点内容测试。"""

    def test_chapter_content_has_system_and_user(self, registry: PromptRegistry):
        node = registry.get_node("chapter-content")
        assert node.system_prompt.strip() != ""
        assert node.user_prompt.strip() != ""
        assert "顶尖的网络小说作家" in node.system_prompt
        assert "{{novel_title}}" in node.user_prompt

    def test_chapter_content_variables(self, registry: PromptRegistry):
        node = registry.get_node("chapter-content")
        var_names = {v.name for v in node.variables}
        assert "novel_title" in var_names
        assert "chapter_number" in var_names
        assert "chapter_outline" in var_names
        assert "target_words" in var_names
        # target_words 有默认值
        tw = next(v for v in node.variables if v.name == "target_words")
        assert tw.default == 2500
        assert tw.required is False

    def test_content_review_output_format_json(self, registry: PromptRegistry):
        node = registry.get_node("content-review")
        assert node.output_format == "json"

    def test_chapter_outline_output_format_markdown(self, registry: PromptRegistry):
        node = registry.get_node("chapter-outline")
        assert node.output_format == "markdown"


class TestRender:
    """变量渲染测试。"""

    def test_render_replaces_variables(self, registry: PromptRegistry):
        system, user = registry.format_prompt("chapter-content", {
            "novel_title": "测试小说",
            "novel_genre": "玄幻",
            "novel_premise": "测试梗概",
            "characters": "主角A",
            "world_settings": "世界",
            "previous_summary": "前文",
            "chapter_number": 1,
            "chapter_title": "第一章",
            "chapter_outline": "大纲",
            "target_words": 2000,
        })
        assert "测试小说" in user
        assert "第一章" in user
        # 不应再有未替换占位
        assert "{{novel_title}}" not in user
        assert "{{chapter_number}}" not in user

    def test_render_applies_default_values(self, registry: PromptRegistry):
        """未提供但有默认值的变量应自动填充。"""
        system, user = registry.format_prompt("chapter-content", {
            "novel_title": "测试",
            "novel_genre": "玄幻",
            "novel_premise": "梗概",
            "characters": "主角",
            "chapter_number": 1,
            "chapter_title": "章",
            "chapter_outline": "纲",
            # target_words 未提供，应取默认 2500
        })
        assert "2500" in user

    def test_render_missing_required_raises_in_strict(self, registry: PromptRegistry):
        """strict 模式下缺失必填变量应抛错。"""
        with pytest.raises(PromptRegistryError, match="缺失必填变量"):
            registry.format_prompt("chapter-content", {}, strict=True)

    def test_render_missing_required_keeps_placeholder_in_non_strict(
        self, registry: PromptRegistry
    ):
        """非 strict 模式下缺失变量保留占位，不抛错。"""
        system, user = registry.format_prompt("chapter-content", {}, strict=False)
        # 占位应保留
        assert "{{novel_title}}" in user


class TestOverride:
    """覆写逻辑测试（sort_order 大的覆盖小的）。"""

    def test_override_by_sort_order(self, tmp_path: Path):
        """同名节点 sort_order 大的应覆盖小的。"""
        nodes_dir = tmp_path / "nodes"
        # 低优先级节点
        low_dir = nodes_dir / "test-node"
        low_dir.mkdir(parents=True)
        (low_dir / "package.yaml").write_text(
            "id: test-node\nname: 低优先级\nsort_order: 5\n", encoding="utf-8"
        )
        (low_dir / "system.md").write_text("低优先级 system", encoding="utf-8")
        (low_dir / "user.md").write_text("低优先级 user", encoding="utf-8")
        # 高优先级节点（同名）
        high_dir = nodes_dir / "test-node-high"
        high_dir.mkdir()
        (high_dir / "package.yaml").write_text(
            "id: test-node\nname: 高优先级\nsort_order: 10\n", encoding="utf-8"
        )
        (high_dir / "system.md").write_text("高优先级 system", encoding="utf-8")
        (high_dir / "user.md").write_text("高优先级 user", encoding="utf-8")

        reg = PromptRegistry(nodes_dir)
        reg.load_all()
        node = reg.get_node("test-node")
        assert node.name == "高优先级"
        assert node.system_prompt == "高优先级 system"

    def test_manual_register_overrides(self, registry: PromptRegistry):
        """手动 register 应覆盖扫描结果。"""
        registry.load_all()
        custom = PromptNode(
            id="chapter-content",
            name="自定义覆写",
            system_prompt="custom system",
            user_prompt="custom user",
        )
        registry.register(custom)
        node = registry.get_node("chapter-content")
        assert node.name == "自定义覆写"
        assert node.system_prompt == "custom system"


class TestErrorHandling:
    """错误处理测试。"""

    def test_get_nonexistent_node(self, registry: PromptRegistry):
        with pytest.raises(PromptRegistryError, match="不存在"):
            registry.get_node("nonexistent-node-xyz")

    def test_missing_package_yaml_skipped(self, tmp_path: Path):
        """缺少 package.yaml 的目录应被跳过（不抛错）。"""
        nodes_dir = tmp_path / "nodes"
        bad_dir = nodes_dir / "bad-node"
        bad_dir.mkdir(parents=True)
        # 只有 system.md，无 package.yaml
        (bad_dir / "system.md").write_text("x", encoding="utf-8")
        reg = PromptRegistry(nodes_dir)
        reg.load_all()  # 不应抛错
        assert not reg.has_node("bad-node")

    def test_nonexistent_dir_warns(self, tmp_path: Path):
        """不存在的目录应警告但不抛错。"""
        reg = PromptRegistry(tmp_path / "nonexistent")
        reg.load_all()  # 不应抛错
        assert reg.list_nodes() == []


class TestPlotPilotNodeIntegrity:
    """PlotPilot 节点完整性测试（抽样验证）。"""

    def test_chapter_prose_generation_has_variables(self, registry: PromptRegistry):
        node = registry.get_node("chapter-prose-generation")
        var_names = {v.name for v in node.variables}
        assert "target_words" in var_names
        assert "chapter_outline" in var_names

    def test_plotpilot_node_has_system_and_user(self, registry: PromptRegistry):
        node = registry.get_node("chapter-prose-generation")
        assert node.system_prompt.strip() != ""
        assert node.user_prompt.strip() != ""

    def test_plotpilot_node_source_field(self, registry: PromptRegistry):
        """PlotPilot 节点 source 字段应保留。"""
        node = registry.get_node("chapter-prose-generation")
        assert node.source == "ai_invocation/chapter.generate.prose"
