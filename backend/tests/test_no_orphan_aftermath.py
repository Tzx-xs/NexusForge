"""Sprint 2.3 RED：验证孤儿代码已删除且不影响主流程。

孤儿代码：
- backend/engine/aftermath/ 整个目录（ChapterAftermathPipeline 从未被引用）
- backend/application/engine/steps/step2_generate_content.py 的 execute 非流式方法
  （GenerationPipeline 只调用 execute_stream，execute 是死代码）
"""
import importlib
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_orphan_aftermath_directory_removed():
    """backend/engine/aftermath/ 目录应被删除。"""
    orphan_dir = BACKEND_DIR / "engine" / "aftermath"
    assert not orphan_dir.exists(), (
        f"孤儿目录应被删除：{orphan_dir}\n"
        "ChapterAftermathPipeline 从未被任何代码引用，是死代码。"
    )


def test_orphan_aftermath_module_unimportable():
    """尝试导入孤儿模块应失败。"""
    with pytest.raises((ImportError, ModuleNotFoundError)):
        importlib.import_module("engine.aftermath.chapter_aftermath_pipeline")


def test_real_aftermath_pipeline_still_importable():
    """删除孤儿后，真实的 AftermathPipeline 应仍可正常导入。"""
    from engine.pipeline.aftermath import AftermathPipeline
    assert AftermathPipeline is not None
    # 验证 run 方法签名未变
    assert hasattr(AftermathPipeline, "run")


def test_step2_execute_dead_code_removed():
    """Step2GenerateContent.execute 不应再包含独立的 LLM 调用逻辑（应委托给 execute_stream）。

    原始问题：execute 与 execute_stream 内部包含重复的 outline+content 生成逻辑，
    GenerationPipeline 实际只调用 execute_stream，execute 是死代码。

    修复：execute 改为消费 execute_stream 事件流，消除重复逻辑。
    """
    import inspect

    from application.engine.steps.step2_generate_content import Step2GenerateContent

    # 验证 execute_stream 仍存在
    assert hasattr(Step2GenerateContent, "execute_stream"), "execute_stream 必须保留"

    # 检查 execute 方法源码：不应再包含独立的 LLM 调用（chat / chat_stream）
    source = inspect.getsource(Step2GenerateContent)

    # 提取 execute 方法的源码段（从 "async def execute" 到下一个 "async def" 之前）
    start = source.find("async def execute(")
    end = source.find("async def execute_stream(")
    assert start != -1 and end != -1, "execute 与 execute_stream 方法都应存在"

    execute_source = source[start:end]

    # execute 方法不应直接调用 LLM（应通过 execute_stream 间接调用）
    assert "self.llm_client.chat(" not in execute_source, (
        "execute 不应直接调用 llm_client.chat，应委托给 execute_stream"
    )
    assert "self.llm_client.chat_stream(" not in execute_source, (
        "execute 不应直接调用 llm_client.chat_stream，应委托给 execute_stream"
    )
    assert "self.prompt_manager.render(" not in execute_source, (
        "execute 不应直接调用 prompt_manager.render，应委托给 execute_stream"
    )
    # execute 应调用 execute_stream
    assert "execute_stream" in execute_source, (
        "execute 应委托给 execute_stream"
    )
