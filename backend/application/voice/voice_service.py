from __future__ import annotations

from typing import Any

from infrastructure.persistence.voice_repo import VoiceRepository

from .voice_drift_detector import VoiceDriftDetector
from .voice_extractor import VoiceExtractor
from .voice_models import VoiceDriftResult, VoiceFingerprint
from .voice_rewriter import VoiceRewriter


class VoiceService:
    """文风服务 - 统一入口"""

    def __init__(self, voice_repo: VoiceRepository | None = None):
        self.extractor = VoiceExtractor()
        self.detector = VoiceDriftDetector()
        self.rewriter = VoiceRewriter()
        self._fingerprints: dict[str, VoiceFingerprint] = {}
        self._repo = voice_repo
        # 启动时从持久层加载已有指纹到内存缓存
        if self._repo is not None:
            for fp in self._repo.list_all():
                self._fingerprints[fp.fingerprint_id] = fp

    def _persist(self, fp: VoiceFingerprint) -> None:
        """将指纹写入持久层（若可用）。"""
        if self._repo is not None:
            self._repo.save(fp)

    def extract_fingerprint(self, texts: list[str], name: str = "default", novel_id: str = "") -> VoiceFingerprint:
        fp = self.extractor.extract(texts, name=name, novel_id=novel_id)
        self._fingerprints[fp.fingerprint_id] = fp
        self._persist(fp)
        return fp

    def detect_drift(self, baseline_id: str, sample_text: str) -> VoiceDriftResult | None:
        baseline = self._fingerprints.get(baseline_id)
        if not baseline:
            return None

        sample_fp = self.extractor.extract([sample_text], name="sample", novel_id=baseline.novel_id)
        return self.detector.detect(baseline, sample_fp)

    def detect_drift_from_fingerprints(self, baseline: VoiceFingerprint, sample: VoiceFingerprint) -> VoiceDriftResult:
        return self.detector.detect(baseline, sample)

    def generate_rewrite_prompt(self, baseline_id: str, target_text: str, drift_dimensions: list[str]) -> str | None:
        baseline = self._fingerprints.get(baseline_id)
        if not baseline:
            return None
        return self.rewriter.generate_rewrite_prompt(baseline, target_text, drift_dimensions)

    async def rewrite_content(
        self,
        baseline_id: str,
        target_text: str,
        drift_dimensions: list[str],
        llm_client,
    ) -> str | None:
        """Phase 5 Task 5.2：调用 LLM 执行文风定向改写。

        Args:
            baseline_id: 基准指纹 ID
            target_text: 待改写正文
            drift_dimensions: 漂移维度列表
            llm_client: LLMClient 实例

        Returns:
            改写后的正文；若 baseline 不存在则返回 None（调用方应保留原文本）。
        """
        baseline = self._fingerprints.get(baseline_id)
        if not baseline:
            return None
        return await self.rewriter.rewrite(baseline, target_text, drift_dimensions, llm_client)

    def generate_style_guide(self, fingerprint_id: str) -> str | None:
        fp = self._fingerprints.get(fingerprint_id)
        if not fp:
            return None
        return self.rewriter.generate_style_guide(fp)

    def merge_fingerprints(self, fps: list[VoiceFingerprint], name: str = "merged") -> VoiceFingerprint:
        if not fps:
            return VoiceFingerprint(name=name)

        total_chars = sum(fp.source_char_count for fp in fps)
        if total_chars == 0:
            return VoiceFingerprint(name=name)

        merged = VoiceFingerprint(name=name, novel_id=fps[0].novel_id)
        weights = [fp.source_char_count / total_chars for fp in fps]

        def weighted_avg(attr: str) -> float:
            return float(sum(getattr(fp, attr) * w for fp, w in zip(fps, weights, strict=False)))

        merged.lexical_richness = weighted_avg("lexical_richness")
        merged.sentence_length_mean = weighted_avg("sentence_length_mean")
        merged.sentence_length_std = weighted_avg("sentence_length_std")
        merged.paragraph_length_mean = weighted_avg("paragraph_length_mean")
        merged.paragraph_length_std = weighted_avg("paragraph_length_std")
        merged.unique_char_ratio = weighted_avg("unique_char_ratio")
        merged.function_word_ratio = weighted_avg("function_word_ratio")
        merged.content_word_ratio = weighted_avg("content_word_ratio")
        merged.dialogue_ratio = weighted_avg("dialogue_ratio")
        merged.narration_ratio = weighted_avg("narration_ratio")
        merged.description_ratio = weighted_avg("description_ratio")
        merged.sentence_structure_diversity = weighted_avg("sentence_structure_diversity")
        merged.clause_density = weighted_avg("clause_density")
        merged.avg_word_per_sentence = weighted_avg("avg_word_per_sentence")

        merged.source_sample_count = sum(fp.source_sample_count for fp in fps)
        merged.source_char_count = total_chars

        all_ngrams = []
        for fp in fps:
            all_ngrams.extend(fp.common_ngrams)
        merged.common_ngrams = list(dict.fromkeys(all_ngrams))[:20]

        all_phrases = []
        for fp in fps:
            all_phrases.extend(fp.signature_phrases)
        merged.signature_phrases = list(dict.fromkeys(all_phrases))[:10]

        all_starts = []
        for fp in fps:
            all_starts.extend(fp.paragraph_starts)
        merged.paragraph_starts = list(dict.fromkeys(all_starts))[:10]

        merged.fingerprint_id = merged.compute_hash()
        self._fingerprints[merged.fingerprint_id] = merged
        self._persist(merged)
        return merged

    def register_fingerprint(self, fp: VoiceFingerprint) -> None:
        self._fingerprints[fp.fingerprint_id] = fp
        self._persist(fp)

    def get_fingerprint(self, fp_id: str) -> VoiceFingerprint | None:
        fp = self._fingerprints.get(fp_id)
        if fp is not None:
            return fp
        # 缓存未命中时回查持久层并回填缓存
        if self._repo is not None:
            fp = self._repo.get_by_id(fp_id)
            if fp is not None:
                self._fingerprints[fp_id] = fp
        return fp

    def list_fingerprints(self) -> list[dict[str, Any]]:
        return [
            {
                "id": fp.fingerprint_id,
                "name": fp.name,
                "novel_id": fp.novel_id,
                "sample_count": fp.source_sample_count,
                "char_count": fp.source_char_count,
            }
            for fp in self._fingerprints.values()
        ]

    def handle_drift(self, drift_result: VoiceDriftResult, chapter_content: str) -> dict[str, Any]:
        """M-25: 处理文风漂移检测结果。

        编排漂移检测后的修正和通知流程。
        返回包含修正建议的字典，供 SSE 推送使用。
        """
        result: dict[str, Any] = {
            "drifted": drift_result.drifted,
            "overall_similarity": drift_result.overall_similarity,
            "drift_dimensions": drift_result.drift_dimensions,
            "rewrite_prompt": None,
            "action": "none",
        }

        if not drift_result.drifted:
            return result

        # 漂移时生成修正动作
        result["action"] = "drift_warning"
        result["drift_dimensions"] = drift_result.drift_dimensions

        # 尝试找到基准指纹以生成改写提示
        fingerprints = self.list_fingerprints()
        if fingerprints:
            fp_id = fingerprints[0].get("id", "")
            result["rewrite_prompt"] = self.generate_rewrite_prompt(
                fp_id, chapter_content, drift_result.drift_dimensions
            )

        return result
