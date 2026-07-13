"""StepResult 三态增强测试

验证：
1. 向后兼容：现有 status 字符串 ("success"/"failed"/"skipped") 仍可用
2. PlotPilot 风格工厂方法：ok() / fail() / skip_step()
3. 语义属性：passed / skipped / failed
4. 新增字段：violations / suggestions / score
"""
import pytest

from engine.pipeline.context import StepResult


class TestStepResultBackwardCompat:
    """向后兼容：现有 status 字符串构造方式仍可用"""

    def test_success_status(self):
        r = StepResult(step_name="x", status="success")
        assert r.status == "success"
        assert r.passed is True
        assert r.failed is False
        assert r.skipped is False

    def test_failed_status(self):
        r = StepResult(step_name="x", status="failed", error="boom")
        assert r.status == "failed"
        assert r.failed is True
        assert r.passed is False

    def test_skipped_status(self):
        r = StepResult(step_name="x", status="skipped")
        assert r.status == "skipped"
        assert r.skipped is True
        assert r.passed is False
        assert r.failed is False

    def test_existing_fields_preserved(self):
        r = StepResult(
            step_name="x",
            status="success",
            duration_ms=42,
            output={"k": 1},
            error=None,
            metadata={"m": 2},
        )
        assert r.duration_ms == 42
        assert r.output == {"k": 1}
        assert r.metadata == {"m": 2}


class TestStepResultFactoryMethods:
    """PlotPilot 风格工厂方法"""

    def test_ok_factory(self):
        r = StepResult.ok(step_name="generate", message="done")
        assert r.step_name == "generate"
        assert r.status == "success"
        assert r.passed is True
        assert r.error is None

    def test_ok_factory_with_output(self):
        r = StepResult.ok(step_name="save", output={"id": 1})
        assert r.output == {"id": 1}
        assert r.passed is True

    def test_fail_factory(self):
        r = StepResult.fail(step_name="validate", message="score too low")
        assert r.step_name == "validate"
        assert r.status == "failed"
        assert r.failed is True
        assert r.error == "score too low"

    def test_fail_factory_with_violations_and_score(self):
        violations = [{"rule": "pov", "detail": "POV 漂移"}]
        r = StepResult.fail(
            step_name="validate_content",
            message="质量不达标",
            score=35.5,
            violations=violations,
        )
        assert r.score == 35.5
        assert r.violations == violations
        assert r.failed is True

    def test_skip_step_factory(self):
        r = StepResult.skip_step(step_name="validate_voice", reason="无基线指纹")
        assert r.step_name == "validate_voice"
        assert r.status == "skipped"
        assert r.skipped is True
        assert r.error is None


class TestStepResultNewFields:
    """新增字段默认值"""

    def test_default_violations_empty(self):
        r = StepResult(step_name="x", status="success")
        assert r.violations == []

    def test_default_suggestions_empty(self):
        r = StepResult(step_name="x", status="success")
        assert r.suggestions == []

    def test_default_score_none(self):
        r = StepResult(step_name="x", status="success")
        assert r.score is None

    def test_independent_default_lists(self):
        """每个实例的默认 list 应独立，不共享"""
        r1 = StepResult(step_name="x", status="success")
        r2 = StepResult(step_name="y", status="success")
        r1.violations.append({"a": 1})
        assert r2.violations == []


class TestStepResultSerialization:
    """序列化兼容"""

    def test_to_dict_includes_new_fields(self):
        r = StepResult(
            step_name="x",
            status="failed",
            error="boom",
            violations=[{"rule": "r1"}],
            suggestions=["fix it"],
            score=20.0,
        )
        d = r.to_dict()
        assert d["violations"] == [{"rule": "r1"}]
        assert d["suggestions"] == ["fix it"]
        assert d["score"] == 20.0

    def test_from_dict_roundtrip(self):
        original = StepResult(
            step_name="validate",
            status="failed",
            error="low",
            violations=[{"rule": "pov"}],
            score=30.0,
        )
        d = original.to_dict()
        restored = StepResult.from_dict(d)
        assert restored.step_name == "validate"
        assert restored.status == "failed"
        assert restored.violations == [{"rule": "pov"}]
        assert restored.score == 30.0
