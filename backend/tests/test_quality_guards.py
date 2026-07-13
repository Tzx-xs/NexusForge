import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from application.audit.audit_service import QualityAuditService


@pytest.mark.asyncio
async def test_audit_service_initialization():
    service = QualityAuditService.with_default_guards()
    guards = service.list_guards()
    assert len(guards) == 8
    guard_names = [g["name"] for g in guards]
    assert "character_consistency" in guard_names
    assert "plot_density" in guard_names
    assert "language_style" in guard_names
    assert "rhythm" in guard_names
    assert "pov" in guard_names
    assert "naming_consistency" in guard_names
    assert "anti_ai" in guard_names
    assert "macro_rhythm" in guard_names


@pytest.mark.asyncio
async def test_run_audit(sample_text, character_names):
    service = QualityAuditService.with_default_guards()
    report = await service.run_audit(
        sample_text,
        context={"character_names": character_names},
    )
    assert report is not None
    assert 0 <= report.overall_score <= 100
    assert len(report.guard_results) == 8
    assert report.total_issues >= 0
    assert report.duration_ms >= 0


@pytest.mark.asyncio
async def test_audit_with_specific_guards(sample_text):
    service = QualityAuditService.with_default_guards()
    report = await service.run_audit(
        sample_text,
        enabled_guards=["anti_ai", "language_style"],
    )
    assert len(report.guard_results) == 2
    guard_names = [r.guard_name for r in report.guard_results]
    assert "anti_ai" in guard_names
    assert "language_style" in guard_names


@pytest.mark.asyncio
async def test_audit_empty_content():
    service = QualityAuditService.with_default_guards()
    report = await service.run_audit("")
    assert report is not None
