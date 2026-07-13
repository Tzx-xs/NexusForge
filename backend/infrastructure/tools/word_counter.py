import re

from .base import BaseTool, TextStats


class WordCounter(BaseTool):
    name = "word_counter"
    description = "字数统计工具：统计中文字数、段落数、对话数等"

    def count_chinese_chars(self, text: str) -> int:
        if not text:
            return 0
        return len(re.findall(r"[\u4e00-\u9fff]", text))

    def count_total_chars(self, text: str) -> int:
        if not text:
            return 0
        return len(text)

    def count_paragraphs(self, text: str) -> int:
        if not text:
            return 0
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return len(paragraphs)

    def count_dialogues(self, text: str) -> int:
        if not text:
            return 0
        pattern = r'[「""]([^」""]*)[」""]'
        matches = re.findall(pattern, text)
        return len(matches)

    def count_sentences(self, text: str) -> int:
        if not text:
            return 0
        sentence_endings = r"[。！？!?…]+"
        sentences = re.split(sentence_endings, text)
        return len([s for s in sentences if s.strip()])

    def get_stats(self, text: str) -> TextStats:
        chinese = self.count_chinese_chars(text)
        total = self.count_total_chars(text)
        paragraphs = self.count_paragraphs(text)
        dialogues = self.count_dialogues(text)
        sentences = self.count_sentences(text)

        avg_paragraph_len = chinese / paragraphs if paragraphs > 0 else 0.0
        dialogue_ratio = dialogues / sentences if sentences > 0 else 0.0

        return TextStats(
            chinese_chars=chinese,
            total_chars=total,
            paragraphs=paragraphs,
            dialogues=dialogues,
            sentences=sentences,
            avg_paragraph_length=round(avg_paragraph_len, 1),
            dialogue_ratio=round(dialogue_ratio, 2),
        )

    def run(self, text: str) -> TextStats:
        return self.get_stats(text)
