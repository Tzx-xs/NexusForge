"""题材包加载器测试 — 验证 extends 继承与 mixins 混入合并。"""
from __future__ import annotations

from pathlib import Path

import pytest

from config.genre_pack_loader import (
    DEFAULT_GENRE_PACKS_DIR,
    GenrePackError,
    GenrePackLoader,
)


@pytest.fixture
def loader() -> GenrePackLoader:
    return GenrePackLoader(DEFAULT_GENRE_PACKS_DIR)


class TestBasicLoad:
    """基础加载测试。"""

    def test_load_base_pack(self, loader: GenrePackLoader):
        pack = loader.load("base")
        assert pack.name == "基础题材包"
        assert "尊重作者原始设定和用户偏好。" in pack.writing_rules
        assert "禁止固定套路名词污染所有题材。" in pack.anti_guidelines
        assert pack.extends is None
        assert pack.motifs == []

    def test_list_packs_includes_all(self, loader: GenrePackLoader):
        packs = loader.list_packs()
        assert "base" in packs
        assert "xuanhuan" in packs
        assert "wuxia" in packs
        assert "romance" in packs
        assert "dushi" in packs
        assert "anti_guidelines" in packs


class TestExtendsInheritance:
    """extends 继承测试。"""

    def test_xuanhuan_inherits_base_writing_rules(self, loader: GenrePackLoader):
        """玄幻包应继承 base 的 writing_rules（追加，不覆盖）。"""
        pack = loader.load("xuanhuan")
        # base 的写作规则应保留
        assert "尊重作者原始设定和用户偏好。" in pack.writing_rules
        assert "冲突、行动和信息增量优先于空泛抒情。" in pack.writing_rules

    def test_xuanhuan_has_own_motifs(self, loader: GenrePackLoader):
        pack = loader.load("xuanhuan")
        assert "境界压迫" in pack.motifs
        assert "宗门资源" in pack.motifs
        assert "血脉与传承" in pack.motifs

    def test_xuanhuan_anti_guidelines_merged(self, loader: GenrePackLoader):
        """玄幻包 anti_guidelines 应包含 base + 自身（追加去重）。"""
        pack = loader.load("xuanhuan")
        # base 的反套路
        assert "禁止固定套路名词污染所有题材。" in pack.anti_guidelines
        # 玄幻自身
        assert "不要机械堆砌境界名词。" in pack.anti_guidelines
        assert "每次升级必须对应具体代价或选择。" in pack.anti_guidelines

    def test_xuanhuan_name_overrides_base(self, loader: GenrePackLoader):
        """子包 name 应覆盖父包。"""
        pack = loader.load("xuanhuan")
        assert pack.name == "玄幻题材包"

    def test_wuxia_inherits_base(self, loader: GenrePackLoader):
        pack = loader.load("wuxia")
        assert pack.name == "武侠题材包"
        assert "恩怨因果" in pack.motifs
        assert "尊重作者原始设定和用户偏好。" in pack.writing_rules


class TestNoDuplicateOnMerge:
    """列表合并去重测试。"""

    def test_anti_guidelines_no_duplicate(self, loader: GenrePackLoader):
        """base.anti_guidelines 中的条目不应在子包结果中重复出现。"""
        pack = loader.load("dushi")
        # "禁止固定套路名词污染所有题材。" 来自 base，应只出现 1 次
        assert pack.anti_guidelines.count("禁止固定套路名词污染所有题材。") == 1


class TestMixins:
    """mixins 混入测试。"""

    def test_anti_guidelines_pack_has_rules(self, loader: GenrePackLoader):
        """anti_guidelines 包继承 base，含 rules 字段。"""
        pack = loader.load("anti_guidelines")
        assert pack.name == "反套路约束包"
        assert "固定示例名词不得进入生产正文。" in pack.rules
        # 继承 base 的 writing_rules
        assert "尊重作者原始设定和用户偏好。" in pack.writing_rules


class TestErrorHandling:
    """错误处理测试。"""

    def test_load_nonexistent_pack(self, loader: GenrePackLoader):
        with pytest.raises(GenrePackError, match="题材包不存在"):
            loader.load("nonexistent_pack_xyz")

    def test_circular_inheritance_detected(
        self, loader: GenrePackLoader, tmp_path: Path
    ):
        """循环继承应被检测并抛错。"""
        # 构造循环：a -> b -> a
        (tmp_path / "a.yaml").write_text(
            "name: A\nextends: b\n", encoding="utf-8"
        )
        (tmp_path / "b.yaml").write_text(
            "name: B\nextends: a\n", encoding="utf-8"
        )
        cyclic_loader = GenrePackLoader(tmp_path)
        with pytest.raises(GenrePackError, match="循环继承"):
            cyclic_loader.load("a")

    def test_self_mixin_rejected(self, loader: GenrePackLoader, tmp_path: Path):
        """mixins 自身应被拒绝。"""
        (tmp_path / "self_mixin.yaml").write_text(
            "name: SelfMixin\nmixins: [self_mixin]\n", encoding="utf-8"
        )
        cyclic_loader = GenrePackLoader(tmp_path)
        with pytest.raises(GenrePackError, match="不能 mixins 自身"):
            cyclic_loader.load("self_mixin")


class TestCustomDir:
    """自定义目录测试。"""

    def test_load_from_custom_dir(self, tmp_path: Path):
        (tmp_path / "custom.yaml").write_text(
            "name: 自定义\nextends: base\nmotifs:\n  - 自定义母题\n",
            encoding="utf-8",
        )
        # 自定义目录需含 base 才能继承
        (tmp_path / "base.yaml").write_text(
            "name: 基础\nwriting_rules:\n  - 规则1\n",
            encoding="utf-8",
        )
        loader = GenrePackLoader(tmp_path)
        pack = loader.load("custom")
        assert pack.name == "自定义"
        assert "自定义母题" in pack.motifs
        assert "规则1" in pack.writing_rules
