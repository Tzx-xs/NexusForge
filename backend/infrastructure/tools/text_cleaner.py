import re

from .base import BaseTool


class TextCleaner(BaseTool):
    name = "text_cleaner"
    description = "文本清洗工具：去除多余空行、统一换行符、清理空白"

    def clean(self, text: str) -> str:
        if not text:
            return ""

        text = text.replace("\r\n", "\n").replace("\r", "\n")

        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

        text = re.sub(r"\n{3,}", "\n\n", text)

        text = text.strip()

        return text

    def normalize_whitespace(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r" +", " ", text).strip()

    def remove_control_chars(self, text: str) -> str:
        if not text:
            return ""
        return "".join(c for c in text if c == "\n" or c == "\t" or ord(c) >= 32)

    def extract_dialogues(self, text: str) -> list:
        if not text:
            return []
        pattern = r'[「""]([^」""]*)[」""]'
        return re.findall(pattern, text)

    def extract_paragraphs(self, text: str) -> list:
        if not text:
            return []
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return paragraphs

    def run(self, text: str) -> str:
        return self.clean(text)
