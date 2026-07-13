import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from application.voice.voice_drift_detector import VoiceDriftDetector
from application.voice.voice_extractor import VoiceExtractor
from application.voice.voice_service import VoiceService


def test_voice_extractor(sample_text):
    extractor = VoiceExtractor()
    fp = extractor.extract([sample_text], name="test")

    assert fp is not None
    assert fp.name == "test"
    assert fp.lexical_richness > 0
    assert fp.sentence_length_mean > 0
    assert fp.source_sample_count == 1
    assert fp.source_char_count > 0
    assert fp.fingerprint_id != ""


def test_voice_extractor_multiple_samples(sample_text):
    extractor = VoiceExtractor()
    sample2 = sample_text + "\n\n第二段更多的内容，用来测试多样本的指纹提取。"
    fp = extractor.extract([sample_text, sample2], name="multi_test")

    assert fp.source_sample_count == 2
    assert fp.source_char_count > len(sample_text)


def test_drift_detector_similar(sample_text):
    extractor = VoiceExtractor()
    fp1 = extractor.extract([sample_text], name="a")
    fp2 = extractor.extract([sample_text], name="b")

    detector = VoiceDriftDetector()
    result = detector.detect(fp1, fp2)

    assert result.overall_similarity > 0.9
    assert result.drifted is False


def test_drift_detector_different(sample_text):
    extractor = VoiceExtractor()
    fp1 = extractor.extract([sample_text], name="original")

    diff_text = """
    这是一段完全不同的文本。用简短的句子。
    没有对话。
    词汇也完全不一样。
    风格差异很大。
    """
    fp2 = extractor.extract([diff_text], name="different")

    detector = VoiceDriftDetector()
    result = detector.detect(fp1, fp2)

    assert 0 <= result.overall_similarity <= 1
    assert len(result.dimension_scores) > 0


def test_voice_service_workflow(sample_text):
    service = VoiceService()

    fp = service.extract_fingerprint([sample_text], name="test_fingerprint")
    assert fp is not None
    assert fp.fingerprint_id != ""

    fps = service.list_fingerprints()
    assert len(fps) >= 1

    retrieved = service.get_fingerprint(fp.fingerprint_id)
    assert retrieved is not None
    assert retrieved.name == "test_fingerprint"

    drift_result = service.detect_drift(fp.fingerprint_id, sample_text)
    assert drift_result is not None

    guide = service.generate_style_guide(fp.fingerprint_id)
    assert guide is not None
    assert len(guide) > 0
