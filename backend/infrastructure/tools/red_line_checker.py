import re

from .base import BaseTool, Violation


class RedLineChecker(BaseTool):
    name = "red_line_checker"
    description = "写作红线检查器：检查15条写作红线规则"

    RED_LINE_RULES = {
        1: {"name": "emotion_naming", "label": "情绪直接命名", "severity": "high"},
        2: {"name": "info_redundancy", "label": "信息重复", "severity": "medium"},
        3: {"name": "passive_voice", "label": "被动语态滥用", "severity": "low"},
        4: {"name": "adverb_abuse", "label": "副词滥用", "severity": "medium"},
        5: {"name": "cliche_expression", "label": "陈词滥调", "severity": "medium"},
        6: {"name": "info_dump", "label": "信息倾销", "severity": "high"},
        7: {"name": "meta_discourse", "label": "元话语", "severity": "high"},
        8: {"name": "telling_not_showing", "label": "叙述替代展示", "severity": "high"},
        9: {"name": "flat_description", "label": "扁平化描写", "severity": "medium"},
        10: {"name": "inconsistent_pov", "label": "视角越界", "severity": "high"},
        11: {"name": "forced_plot", "label": "剧情推进生硬", "severity": "high"},
        12: {"name": "unnatural_dialogue", "label": "对话不自然", "severity": "medium"},
        13: {"name": "weak_conflict", "label": "冲突薄弱", "severity": "high"},
        14: {"name": "pacing_issue", "label": "节奏问题", "severity": "medium"},
        15: {"name": "logical_hole", "label": "逻辑漏洞", "severity": "high"},
    }

    EMOTION_WORDS = [
        "愤怒",
        "悲伤",
        "高兴",
        "快乐",
        "害怕",
        "恐惧",
        "担心",
        "焦虑",
        "紧张",
        "激动",
        "感动",
        "兴奋",
        "痛苦",
        "绝望",
        "失落",
        "沮丧",
        "开心",
        "幸福",
        "满足",
        "遗憾",
        "后悔",
        "羞愧",
        "骄傲",
        "自豪",
        "感到",
        "觉得",
        "心里想",
        "心中暗道",
    ]

    META_DISCOURSE_WORDS = [
        "只见",
        "却见",
        "这时",
        "突然",
        "忽然",
        "原来",
        "话说",
        "且说",
        "再说",
        "只见那",
    ]

    ADVERBS = [
        "非常",
        "十分",
        "特别",
        "极其",
        "相当",
        "格外",
        "分外",
        "更加",
        "渐渐地",
        "慢慢地",
        "缓缓地",
        "轻轻地",
        "悄悄地",
        "默默地",
        "紧紧地",
        "深深地",
        "大大地",
        "长长地",
    ]

    CLICHES = [
        "光阴似箭",
        "日月如梭",
        "转眼间",
        "刹那间",
        "一瞬间",
        "晴天霹雳",
        "五雷轰顶",
        "心如刀绞",
        "泪如雨下",
        "说时迟那时快",
        "与此同时",
    ]

    def check_emotion_naming(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations

        count = 0
        matched_words = []
        for word in self.EMOTION_WORDS:
            matches = [m.start() for m in re.finditer(re.escape(word), text)]
            if matches:
                count += len(matches)
                matched_words.append(f"{word}({len(matches)})")

        if count >= 3:
            violations.append(
                Violation(
                    rule_id=1,
                    rule_name="emotion_naming",
                    description=f"情绪直接命名{count}次（{', '.join(matched_words[:5])}），建议通过动作、表情、环境描写展示情绪",
                    severity="high",
                )
            )
        return violations

    def check_meta_discourse(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations

        count = 0
        matched_words = []
        for word in self.META_DISCOURSE_WORDS:
            matches = [m.start() for m in re.finditer(re.escape(word), text)]
            if matches:
                count += len(matches)
                matched_words.append(f"{word}({len(matches)})")

        if count >= 3:
            violations.append(
                Violation(
                    rule_id=7,
                    rule_name="meta_discourse",
                    description=f"元话语出现{count}次（{', '.join(matched_words[:5])}），建议删除元话语，直接呈现场景",
                    severity="high",
                )
            )
        return violations

    def check_adverb_abuse(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations

        count = 0
        matched_words = []
        for word in self.ADVERBS:
            matches = [m.start() for m in re.finditer(re.escape(word), text)]
            if matches:
                count += len(matches)
                matched_words.append(f"{word}({len(matches)})")

        total_chars = len(text)
        ratio = count / max(total_chars, 1) * 100

        if ratio > 0.5:
            violations.append(
                Violation(
                    rule_id=4,
                    rule_name="adverb_abuse",
                    description=f"副词使用偏多（{count}次，占比{ratio:.2f}%），涉及：{', '.join(matched_words[:5])}",
                    severity="medium",
                )
            )
        return violations

    def check_cliche_expression(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations

        count = 0
        matched = []
        for phrase in self.CLICHES:
            matches = [m.start() for m in re.finditer(re.escape(phrase), text)]
            if matches:
                count += len(matches)
                matched.append(f"{phrase}({len(matches)})")

        if count >= 2:
            violations.append(
                Violation(
                    rule_id=5,
                    rule_name="cliche_expression",
                    description=f"陈词滥调出现{count}次（{', '.join(matched[:5])}），建议使用原创表达",
                    severity="medium",
                )
            )
        return violations

    def check_info_redundancy(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(paragraphs) < 2:
            return violations

        dup_count = 0
        dup_phrases = set()
        for i in range(len(paragraphs)):
            for j in range(i + 1, min(i + 3, len(paragraphs))):
                words_i = set(re.findall(r"[\u4e00-\u9fff]{4,}", paragraphs[i]))
                words_j = set(re.findall(r"[\u4e00-\u9fff]{4,}", paragraphs[j]))
                common = words_i & words_j
                if len(common) >= 3:
                    dup_count += 1
                    dup_phrases.update(list(common)[:3])

        if dup_count >= 2:
            violations.append(
                Violation(
                    rule_id=2,
                    rule_name="info_redundancy",
                    description=f"检测到{dup_count}处信息重复，重复短语包括：{', '.join(list(dup_phrases)[:5])}",
                    severity="medium",
                )
            )
        return violations

    def check_unnatural_dialogue(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        if not text:
            return violations

        pattern = r'[「""]([^」""]*)[」""]'
        dialogues = re.findall(pattern, text)
        if not dialogues:
            return violations

        long_dialogues = [d for d in dialogues if len(d) > 100]
        if len(long_dialogues) >= 2:
            violations.append(
                Violation(
                    rule_id=12,
                    rule_name="unnatural_dialogue",
                    description=f"有{len(long_dialogues)}段对话过长（>100字），建议拆分对话或穿插动作描写",
                    severity="medium",
                )
            )
        return violations

    def check(self, text: str) -> list[Violation]:
        all_violations: list[Violation] = []
        all_violations.extend(self.check_emotion_naming(text))
        all_violations.extend(self.check_meta_discourse(text))
        all_violations.extend(self.check_adverb_abuse(text))
        all_violations.extend(self.check_cliche_expression(text))
        all_violations.extend(self.check_info_redundancy(text))
        all_violations.extend(self.check_unnatural_dialogue(text))
        return all_violations

    def get_rule_info(self, rule_id: int) -> dict | None:
        return self.RED_LINE_RULES.get(rule_id)

    def run(self, text: str) -> list[Violation]:
        return self.check(text)
