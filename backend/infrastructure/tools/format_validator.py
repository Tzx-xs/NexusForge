import re

from .base import BaseTool, Violation


class FormatValidator(BaseTool):
    name = "format_validator"
    description = "格式校验器：校验文本格式规范"

    def check_line_length(self, text: str, max_len: int = 80) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations
        for i, line in enumerate(text.split("\n"), 1):
            if len(line.strip()) > max_len:
                violations.append(
                    Violation(
                        rule_id=101,
                        rule_name="line_too_long",
                        description=f"第{i}行过长（{len(line.strip())}字），建议控制在{max_len}字以内",
                        severity="low",
                        position={"line": i},
                    )
                )
        return violations

    def check_paragraph_structure(self, text: str, min_paragraphs: int = 3) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations
        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(paragraphs) < min_paragraphs:
            violations.append(
                Violation(
                    rule_id=102,
                    rule_name="too_few_paragraphs",
                    description=f"段落数过少（{len(paragraphs)}段），建议至少{min_paragraphs}段",
                    severity="medium",
                )
            )
        return violations

    def check_punctuation_consistency(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations

        half_width_punct = re.findall(r"[!?]", text)
        full_width_punct = re.findall(r"[！？]", text)

        if half_width_punct and full_width_punct:
            violations.append(
                Violation(
                    rule_id=103,
                    rule_name="mixed_punctuation",
                    description=f"标点符号混用（半角{len(half_width_punct)}处/全角{len(full_width_punct)}处），建议统一使用全角标点",
                    severity="medium",
                )
            )
        return violations

    def check_dialogue_format(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations

        unmatched = []
        stack = []
        for i, c in enumerate(text):
            if c in '「"':
                stack.append((c, i))
            elif c in '」"':
                if stack:
                    stack.pop()
                else:
                    unmatched.append(("extra_close", i))

        for _c, pos in stack:
            unmatched.append(("unclosed", pos))

        for kind, pos in unmatched[:5]:
            line_num = text[:pos].count("\n") + 1
            if kind == "unclosed":
                violations.append(
                    Violation(
                        rule_id=104,
                        rule_name="unclosed_dialogue",
                        description=f"第{line_num}行有未闭合的对话引号",
                        severity="high",
                        position={"line": line_num, "pos": pos},
                    )
                )
            else:
                violations.append(
                    Violation(
                        rule_id=105,
                        rule_name="extra_dialogue_close",
                        description=f"第{line_num}行有多余的对话引号闭合",
                        severity="high",
                        position={"line": line_num, "pos": pos},
                    )
                )

        return violations

    def validate(self, text: str) -> list[Violation]:
        all_violations: list[Violation] = []
        all_violations.extend(self.check_line_length(text))
        all_violations.extend(self.check_paragraph_structure(text))
        all_violations.extend(self.check_punctuation_consistency(text))
        all_violations.extend(self.check_dialogue_format(text))
        return all_violations

    def run(self, text: str) -> list[Violation]:
        return self.validate(text)
