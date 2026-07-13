"""Phase 5 Task 5.2：文风漂移定向改写闭环测试

验证点：
1. 检测到漂移 + 注入 llm_client → 触发改写循环
2. 改写后不再漂移 → 提前终止循环
3. 改写后仍漂移 → 最多 max_attempts 轮后终止
4. 改写后的内容覆盖 ctx.generated_content
5. 注入 chapter_repo → 改写结果回写到章节
6. 未注入 llm_client → 跳过改写（仅检测漂移）
7. LLM 异常 → 回退原文本，不破坏管线
8. 无基准指纹 → skipped
9. 无内容 → skipped
"""
import pytest

from application.voice.voice_models import VoiceDriftResult, VoiceFingerprint
from engine.pipeline.context import PipelineContext
from engine.pipeline.steps import ValidateVoiceStep, VOICE_REWRITE_MAX_ATTEMPTS


# ─── 测试桩 ────────────────────────────────────────────────────────
class _FakeLLMClient:
    """按预设序列返回改写结果的假 LLM client"""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.call_count = 0
        self.last_prompt: str | None = None
        self.last_system_prompt: str | None = None

    async def chat(self, prompt, system_prompt="", **kwargs):
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        if self.call_count <= len(self._responses):
            return self._responses[self.call_count - 1]
        return "fallback"


class _FakeVoiceService:
    """可控的 VoiceService 桩：控制 detect_drift 行为，rewrite_content 走真实 VoiceRewriter"""

    def __init__(
        self,
        fingerprint_id: str = "fp-1",
        drift_sequence: list[VoiceDriftResult | None] | None = None,
        baseline_fp: VoiceFingerprint | None = None,
    ):
        from application.voice.voice_rewriter import VoiceRewriter
        self._fp_id = fingerprint_id
        self._drift_sequence = drift_sequence or []
        self._baseline_fp = baseline_fp or VoiceFingerprint(
            name="default",
            sentence_length_mean=15.0,
            dialogue_ratio=0.4,
        )
        self._rewriter = VoiceRewriter()  # 走真实改写逻辑，LLM 用桩
        self.drift_call_count = 0
        self.rewrite_call_count = 0

    def list_fingerprints(self):
        return [{"id": self._fp_id, "name": "default"}]

    def detect_drift(self, baseline_id, sample_text):
        if self.drift_call_count < len(self._drift_sequence):
            result = self._drift_sequence[self.drift_call_count]
        else:
            result = self._drift_sequence[-1] if self._drift_sequence else None
        self.drift_call_count += 1
        return result

    async def rewrite_content(self, baseline_id, target_text, drift_dimensions, llm_client):
        self.rewrite_call_count += 1
        return await self._rewriter.rewrite(
            self._baseline_fp, target_text, drift_dimensions, llm_client
        )


class _FakeChapterRepo:
    """记录 update 调用的章节仓库桩"""

    def __init__(self):
        self.chapters: dict[str, object] = {}
        self.updated_ids: list[str] = []

    def get_by_id(self, chapter_id):
        return self.chapters.get(chapter_id)

    def update(self, chapter):
        self.updated_ids.append(chapter.id)
        self.chapters[chapter.id] = chapter
        return chapter


def _drift(similarity: float = 0.5, drifted: bool = True, dims: list[str] | None = None) -> VoiceDriftResult:
    return VoiceDriftResult(
        drifted=drifted,
        overall_similarity=similarity,
        dimension_scores={},
        drift_dimensions=dims or ["sentence_length_mean"],
        details={},
    )


# ═══════════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════════
class TestVoiceRewriteLoop:
    """文风漂移定向改写闭环"""

    @pytest.mark.asyncio
    async def test_drift_triggers_rewrite_and_resolves(self):
        """漂移→改写→复检通过：1 轮改写即解决，提前终止"""
        # 第1次 detect_drift：漂移（触发改写）
        # 第2次 detect_drift：不再漂移（改写后复检通过）
        voice_svc = _FakeVoiceService(
            drift_sequence=[_drift(0.4, True), _drift(0.9, False)],
        )
        llm = _FakeLLMClient(["改写后的优质正文，句式多样。"])

        step = ValidateVoiceStep(voice_svc, llm_client=llm, max_attempts=2)
        ctx = PipelineContext(novel_id="n1", chapter_id="c1", chapter_index=1)
        ctx.set("generated_content", "原始漂移正文")

        result = await step.execute(ctx)

        assert result.status == "success"
        assert result.output["drifted"] is False  # 改写后不再漂移
        assert result.output["rewrite"]["applied"] is True
        assert result.output["rewrite"]["attempts"] == 1
        assert result.output["rewrite"]["final_drifted"] is False
        # LLM 被调用 1 次
        assert llm.call_count == 1
        # ctx.generated_content 被覆盖
        assert ctx.get("generated_content") == "改写后的优质正文，句式多样。"
        assert ctx.get("voice_rewrite_applied") is True
        # 原始内容保留供诊断
        assert ctx.get("original_content_before_voice_rewrite") == "原始漂移正文"

    @pytest.mark.asyncio
    async def test_drift_persists_after_max_attempts(self):
        """改写后仍漂移：达到 max_attempts 轮后终止，保留最后一次结果"""
        # 3 次 detect_drift 全部漂移：初始检测 + 2 轮复检
        voice_svc = _FakeVoiceService(
            drift_sequence=[
                _drift(0.3, True),   # 初始检测
                _drift(0.4, True),   # 第1轮改写后复检
                _drift(0.45, True),  # 第2轮改写后复检
            ],
        )
        llm = _FakeLLMClient(["改写1", "改写2"])

        step = ValidateVoiceStep(voice_svc, llm_client=llm, max_attempts=2)
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "原始")

        result = await step.execute(ctx)

        assert result.output["drifted"] is True  # 仍漂移
        assert result.output["rewrite"]["attempts"] == 2
        assert result.output["rewrite"]["final_drifted"] is True
        # LLM 被调用 2 次（等于 max_attempts）
        assert llm.call_count == 2
        # ctx 保留最后一次改写结果
        assert ctx.get("generated_content") == "改写2"

    @pytest.mark.asyncio
    async def test_no_llm_client_skips_rewrite(self):
        """未注入 llm_client → 仅检测漂移，不触发改写"""
        voice_svc = _FakeVoiceService(drift_sequence=[_drift(0.4, True)])

        step = ValidateVoiceStep(voice_svc, llm_client=None)
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "原始")

        result = await step.execute(ctx)

        assert result.status == "success"
        assert result.output["drifted"] is True
        assert result.output["rewrite"]["applied"] is False
        # ctx 内容未变
        assert ctx.get("generated_content") == "原始"
        assert ctx.get("voice_rewrite_applied") is None

    @pytest.mark.asyncio
    async def test_chapter_repo_persists_rewrite(self):
        """注入 chapter_repo → 改写结果回写到章节"""
        voice_svc = _FakeVoiceService(
            drift_sequence=[_drift(0.4, True), _drift(0.95, False)],
        )
        llm = _FakeLLMClient(["改写后的正文"])

        # 准备一个假 chapter 对象
        class _FakeChapter:
            def __init__(self, cid, content, wc):
                self.id = cid
                self.content = content
                self.word_count = wc

        repo = _FakeChapterRepo()
        repo.chapters["c1"] = _FakeChapter("c1", "原始", 2)

        step = ValidateVoiceStep(
            voice_svc, llm_client=llm, chapter_repo=repo, max_attempts=2
        )
        ctx = PipelineContext(novel_id="n1", chapter_id="c1", chapter_index=1)
        ctx.set("generated_content", "原始")

        await step.execute(ctx)

        # 章节内容被更新
        assert "c1" in repo.updated_ids
        updated_chapter = repo.chapters["c1"]
        assert updated_chapter.content == "改写后的正文"
        assert updated_chapter.word_count == len("改写后的正文")

    @pytest.mark.asyncio
    async def test_llm_returns_empty_falls_back_to_original(self):
        """LLM 返回空字符串 → VoiceRewriter.rewrite 回退原文本，停止改写"""
        voice_svc = _FakeVoiceService(
            drift_sequence=[_drift(0.4, True)],
        )
        # LLM 返回空字符串
        llm = _FakeLLMClient([""])

        step = ValidateVoiceStep(voice_svc, llm_client=llm, max_attempts=3)
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "原始正文")

        result = await step.execute(ctx)

        # VoiceRewriter.rewrite 对空返回会回退 target_text，即 rewritten == current_content
        # 改写循环检测到 unchanged，停止
        assert result.output["rewrite"]["applied"] is False
        # 内容未变
        assert ctx.get("generated_content") == "原始正文"

    @pytest.mark.asyncio
    async def test_llm_exception_does_not_break_pipeline(self):
        """LLM 抛异常 → 改写循环 break，管线不破坏，内容不变"""
        class _ExplodingLLM:
            async def chat(self, prompt, system_prompt="", **kwargs):
                raise RuntimeError("LLM 服务不可用")

        voice_svc = _FakeVoiceService(
            drift_sequence=[_drift(0.4, True)],
        )

        step = ValidateVoiceStep(voice_svc, llm_client=_ExplodingLLM(), max_attempts=2)
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "原始正文")

        result = await step.execute(ctx)

        # 异常被捕获，step 返回 success（软失败语义）
        assert result.status == "success"
        # 改写未生效
        assert result.output["rewrite"]["applied"] is False
        assert ctx.get("generated_content") == "原始正文"

    @pytest.mark.asyncio
    async def test_no_baseline_fingerprint_returns_success_with_note(self):
        """无基准指纹 → success + note（新书未建指纹的正常场景，不改写）"""
        class _EmptyVoiceService:
            def list_fingerprints(self):
                return []

        step = ValidateVoiceStep(_EmptyVoiceService(), llm_client=_FakeLLMClient([]))
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "内容")

        result = await step.execute(ctx)

        # 无基准指纹是正常情况（新书），返回 success + note，不触发改写
        assert result.status == "success"
        assert "note" in result.output

    @pytest.mark.asyncio
    async def test_empty_content_skipped(self):
        """无内容 → skipped"""
        voice_svc = _FakeVoiceService()

        step = ValidateVoiceStep(voice_svc, llm_client=_FakeLLMClient([]))
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "")

        result = await step.execute(ctx)

        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_no_drift_no_rewrite(self):
        """初始检测无漂移 → 不触发改写"""
        voice_svc = _FakeVoiceService(
            drift_sequence=[_drift(0.95, False)],
        )
        llm = _FakeLLMClient([])

        step = ValidateVoiceStep(voice_svc, llm_client=llm)
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "正常正文")

        result = await step.execute(ctx)

        assert result.output["drifted"] is False
        assert llm.call_count == 0  # LLM 未被调用
        assert ctx.get("generated_content") == "正常正文"

    def test_default_max_attempts_constant(self):
        """VOICE_REWRITE_MAX_ATTEMPTS 常量值为 2"""
        assert VOICE_REWRITE_MAX_ATTEMPTS == 2


class TestVoiceRewriterRewrite:
    """直接测试 VoiceRewriter.rewrite 方法"""

    @pytest.mark.asyncio
    async def test_rewrite_calls_llm_with_prompt(self):
        from application.voice.voice_rewriter import VoiceRewriter
        from application.voice.voice_models import VoiceFingerprint

        baseline = VoiceFingerprint(
            name="default",
            sentence_length_mean=15.0,
            dialogue_ratio=0.4,
            signature_phrases=["剑光一闪"],
        )
        rewriter = VoiceRewriter()
        llm = _FakeLLMClient(["改写后的内容"])

        result = await rewriter.rewrite(baseline, "原始内容", ["sentence_length_mean"], llm)

        assert result == "改写后的内容"
        assert llm.call_count == 1
        # prompt 应包含 baseline 的句长目标
        assert "15" in llm.last_prompt
        # system_prompt 应包含编辑角色设定
        assert "编辑" in llm.last_system_prompt

    @pytest.mark.asyncio
    async def test_rewrite_strips_markdown_code_fence(self):
        from application.voice.voice_rewriter import VoiceRewriter
        from application.voice.voice_models import VoiceFingerprint

        baseline = VoiceFingerprint(name="default")
        rewriter = VoiceRewriter()
        # LLM 用 ``` 包裹返回
        llm = _FakeLLMClient(["```\n改写后的内容\n```"])

        result = await rewriter.rewrite(baseline, "原始", [], llm)

        assert result == "改写后的内容"

    @pytest.mark.asyncio
    async def test_rewrite_falls_back_on_exception(self):
        from application.voice.voice_rewriter import VoiceRewriter
        from application.voice.voice_models import VoiceFingerprint

        baseline = VoiceFingerprint(name="default")
        rewriter = VoiceRewriter()

        class _BoomLLM:
            async def chat(self, prompt, system_prompt="", **kwargs):
                raise RuntimeError("boom")

        result = await rewriter.rewrite(baseline, "原始内容", ["dialogue_ratio"], _BoomLLM())

        # 异常时回退原文本
        assert result == "原始内容"
