"""测试审计反馈注入（BLOCK-02）。

验证：
- _format_audit_feedback() 正确格式化含多条 issue 的审计报告
- 审计不通过时 audit_feedback 被注入到重写上下文
- _generate_chapter() 接受 audit_feedback 参数
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from application.engine.autonomous_writer import AutonomousWritingEngine

# ========== _format_audit_feedback 单元测试 ==========

def test_format_audit_feedback_with_multiple_issues():
    """验证 _format_audit_feedback() 输出包含所有 issue。"""
    audit_report = {
        "overall_score": 45.0,
        "passed": False,
        "guard_results": [
            {
                "guard_name": "红线检查",
                "issues": [
                    {"description": "出现'苟'字在第3段"},
                    {"description": "主角直接使用了星渊能力描述"},
                ],
            },
            {
                "guard_name": "连贯性检查",
                "issues": [
                    {"description": "与前一章结尾情绪不衔接"},
                ],
            },
            {
                "guard_name": "空护栏",
                "issues": [],  # 无 issue 的护栏应被跳过
            },
        ],
    }

    # Arrange: 创建一个最小化 engine 实例
    engine = AutonomousWritingEngine(chapter_service=None)

    # Act
    feedback = engine._format_audit_feedback(audit_report)

    # Assert
    assert "## 上一版审查反馈" in feedback
    assert "以下问题需要在重写时修正" in feedback
    assert "[红线检查]" in feedback
    assert "[连贯性检查]" in feedback
    assert "出现'苟'字在第3段" in feedback
    assert "主角直接使用了星渊能力描述" in feedback
    assert "与前一章结尾情绪不衔接" in feedback
    assert "空护栏" not in feedback  # 无 issue 的护栏不出现
    assert "请针对性修正后重新生成" in feedback
    # 验证编号连续
    assert "1. " in feedback
    assert "2. " in feedback
    assert "3. " in feedback


def test_format_audit_feedback_empty_guard_results():
    """验证 guard_results 为空时的降级格式化。"""
    audit_report = {
        "overall_score": 55.0,
        "passed": False,
        "guard_results": [],
    }

    engine = AutonomousWritingEngine(chapter_service=None)
    feedback = engine._format_audit_feedback(audit_report)

    assert "总分: 55.0" in feedback
    assert "请针对性修正后重新生成" in feedback


def test_format_audit_feedback_no_guard_results_key():
    """验证缺少 guard_results 键时的降级处理。"""
    audit_report = {
        "overall_score": 30.0,
        "passed": False,
    }

    engine = AutonomousWritingEngine(chapter_service=None)
    feedback = engine._format_audit_feedback(audit_report)

    assert "总分: 30.0" in feedback
    assert "请针对性修正后重新生成" in feedback


def test_format_audit_feedback_handles_non_dict_issues():
    """验证 issue 为非 dict 类型时的格式化。"""
    audit_report = {
        "overall_score": 50.0,
        "passed": False,
        "guard_results": [
            {
                "guard_name": "风格检查",
                "issues": ["段落过长", "对话占比过低"],
            },
        ],
    }

    engine = AutonomousWritingEngine(chapter_service=None)
    feedback = engine._format_audit_feedback(audit_report)

    assert "1. [风格检查] 段落过长" in feedback
    assert "2. [风格检查] 对话占比过低" in feedback


def test_format_audit_feedback_all_issues_present():
    """Mock AuditReport(passed=False) 含3条 issue，验证输出包含所有 issue。"""
    audit_report = {
        "overall_score": 42.5,
        "passed": False,
        "guard_results": [
            {
                "guard_name": "字数检查",
                "issues": [{"description": "字数不足3000（实际: 2150）"}],
            },
            {
                "guard_name": "结构检查",
                "issues": [{"description": "四节拍缺失'合'段"}, {"description": "爽点密度不足"}],
            },
        ],
    }

    engine = AutonomousWritingEngine(chapter_service=None)
    feedback = engine._format_audit_feedback(audit_report)

    assert "字数不足3000（实际: 2150）" in feedback
    assert "四节拍缺失'合'段" in feedback
    assert "爽点密度不足" in feedback
    # 共3条 issue
    assert feedback.count("\n") >= 5  # 标题 + 说明 + 3 issues + 空行 + 结尾


# ========== _generate_chapter 参数传递测试 ==========

class MockChapterServiceForAudit:
    """Mock ChapterService 用于验证 audit_feedback 传递。"""

    def __init__(self):
        self.last_audit_feedback = None

    async def generate_chapter(self, novel_id: str, audit_feedback: str = ""):
        self.last_audit_feedback = audit_feedback
        return type(
            "MockChapter",
            (),
            {
                "id": "ch_test",
                "content": "测试内容",
                "word_count": 300,
            },
        )()


@pytest.mark.asyncio
async def test_generate_chapter_passes_audit_feedback():
    """验证 _generate_chapter() 将 audit_feedback 传递给 chapter_service。"""
    mock_service = MockChapterServiceForAudit()
    engine = AutonomousWritingEngine(chapter_service=mock_service)
    status = engine.create_session("novel_test")

    feedback = "## 审查反馈\n1. 问题A\n2. 问题B"
    await engine._generate_chapter(status, 1, audit_feedback=feedback)

    assert mock_service.last_audit_feedback == feedback


@pytest.mark.asyncio
async def test_generate_chapter_empty_audit_feedback():
    """验证不传 audit_feedback 时默认为空字符串。"""
    mock_service = MockChapterServiceForAudit()
    engine = AutonomousWritingEngine(chapter_service=mock_service)
    status = engine.create_session("novel_test")

    await engine._generate_chapter(status, 1)

    assert mock_service.last_audit_feedback == ""
