"""Sprint 2.1 RED：验证 GenerationPipeline 在 SSE 流式生成完成后触发 AftermathPipeline。

核心问题：
- 用户交互路径（SSE 流式）走 GenerationPipeline，不触发 AftermathPipeline
- 导致 SSE 生成的章节无摘要/伏笔/记忆/快照
- 修复：在 GenerationPipeline.generate_content_stream 完成后挂载 AftermathPipeline.run
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from application.engine.generation_pipeline import GenerationPipeline


@pytest.fixture
def mock_deps():
    """构造 GenerationPipeline 所需的全部 Mock 依赖。"""
    llm_client = MagicMock()
    llm_client.chat = AsyncMock(return_value="大纲文本")
    # execute_stream 内部调用 chat_stream，返回 token 流
    async def fake_chat_stream(_prompt):
        for tok in ["正", "文", "内容"]:
            yield tok
    llm_client.chat_stream = fake_chat_stream

    prompt_manager = MagicMock()
    prompt_manager.render = MagicMock(return_value="rendered prompt")
    prompt_manager.get_prompt = MagicMock(return_value="prompt")

    context_builder = MagicMock()
    context_builder.build_generation_context = MagicMock(
        return_value={"novel_id": "n1", "novel_title": "测试小说", "chapter_outline": ""}
    )

    chapter_repo = MagicMock()
    chapter = MagicMock()
    chapter.id = "ch1"
    chapter.novel_id = "n1"
    chapter.title = "测试章节"
    chapter.content = ""
    chapter.outline = ""
    chapter.word_count = 0
    chapter.number = 1
    chapter_repo.get_by_id = MagicMock(return_value=chapter)
    chapter_repo.update = MagicMock(return_value=chapter)

    review_repo = MagicMock()

    return {
        "llm_client": llm_client,
        "prompt_manager": prompt_manager,
        "context_builder": context_builder,
        "chapter_repo": chapter_repo,
        "review_repo": review_repo,
    }


def _collect_streaming_events(gen):
    """辅助：收集 generate_content_stream 产生的全部事件。"""
    events = []

    async def _run():
        async for event_type, data in gen:
            events.append((event_type, data))

    asyncio.run(_run())
    return events


@pytest.mark.asyncio
async def test_generation_pipeline_calls_aftermath_on_complete(mock_deps):
    """SSE 生成完成后应调用 AftermathPipeline.run。"""
    aftermath_pipeline = MagicMock()
    aftermath_pipeline.run = AsyncMock(return_value=MagicMock())

    pipeline = GenerationPipeline(
        aftermath_pipeline=aftermath_pipeline,
        max_retries=0,
        **mock_deps,
    )

    events = []
    async for event_type, data in pipeline.generate_content_stream("ch1"):
        events.append((event_type, data))

    # 必须有 complete 事件
    assert any(t == "complete" for t, _ in events), "应产生 complete 事件"

    # AftermathPipeline.run 必须被调用一次
    assert aftermath_pipeline.run.call_count == 1, (
        f"aftermath_pipeline.run 应被调用 1 次，实际 {aftermath_pipeline.run.call_count} 次"
    )

    # 调用参数：第一个是 PipelineContext，第二个是章节内容字符串
    call_args = aftermath_pipeline.run.call_args
    ctx_arg = call_args.args[0]
    content_arg = call_args.args[1]
    assert ctx_arg is not None, "第一参数应为 PipelineContext"
    assert isinstance(content_arg, str), f"第二参数应为章节内容字符串，实际 {type(content_arg).__name__}"
    assert len(content_arg) > 0, "章节内容不应为空"


@pytest.mark.asyncio
async def test_aftermath_failure_does_not_block_main_flow(mock_deps):
    """AftermathPipeline 抛异常时，主流程不应阻塞，complete 事件仍应产生。"""
    aftermath_pipeline = MagicMock()
    aftermath_pipeline.run = AsyncMock(side_effect=RuntimeError("aftermath boom"))

    pipeline = GenerationPipeline(
        aftermath_pipeline=aftermath_pipeline,
        max_retries=0,
        **mock_deps,
    )

    events = []
    async for event_type, data in pipeline.generate_content_stream("ch1"):
        events.append((event_type, data))

    # AftermathPipeline 异常不应导致 error 事件
    error_events = [e for e in events if e[0] == "error"]
    aftermath_errors = [e for e in error_events if "aftermath boom" in str(e[1])]
    assert len(aftermath_errors) == 0, (
        f"AftermathPipeline 异常不应冒泡到客户端，但出现：{aftermath_errors}"
    )

    # complete 事件仍应产生
    assert any(t == "complete" for t, _ in events), (
        "AftermathPipeline 异常时仍应产生 complete 事件"
    )


@pytest.mark.asyncio
async def test_aftermath_pipeline_optional(mock_deps):
    """未注入 aftermath_pipeline 时，GenerationPipeline 仍可正常工作（向后兼容）。"""
    pipeline = GenerationPipeline(
        aftermath_pipeline=None,
        max_retries=0,
        **mock_deps,
    )

    events = []
    async for event_type, data in pipeline.generate_content_stream("ch1"):
        events.append((event_type, data))

    # 应正常完成
    assert any(t == "complete" for t, _ in events), (
        "未注入 aftermath_pipeline 时仍应正常完成"
    )
