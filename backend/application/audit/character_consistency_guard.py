from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult, GuardSeverity


class CharacterConsistencyGuard(BaseGuard):
    """角色一致性护栏

    检测：
    - 角色人设偏差（基于角色档案）
    - 角色行为一致性
    - 死亡角色出场检测
    - 角色能力设定一致性
    """

    name = "character_consistency"
    description = "角色一致性检测"
    weight = 2.0

    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        issues: list[GuardIssue] = []
        paragraphs = self._split_paragraphs(content)

        characters = context.get("characters", [])
        dead_characters = context.get("dead_characters", [])
        character_traits = context.get("character_traits", {})

        death_issues = self._check_dead_characters(content, dead_characters, paragraphs, issues)

        name_mentions = self._analyze_character_mentions(content, characters, paragraphs, issues)

        trait_score = self._check_trait_consistency(content, character_traits, issues)

        overall_score = death_issues * 0.4 + name_mentions * 0.3 + trait_score * 0.3

        return self._create_result(
            score=round(overall_score, 1),
            issues=issues[:20],
            metadata={
                "death_issue_score": round(death_issues, 1),
                "name_consistency_score": round(name_mentions, 1),
                "trait_consistency_score": round(trait_score, 1),
                "character_count": len(characters),
            },
        )

    def _check_dead_characters(
        self, content: str, dead_chars: list[str], paragraphs: list[str], issues: list[GuardIssue]
    ) -> float:
        if not dead_chars:
            return 100.0

        score = 100.0
        flashback_indicators = ["回忆", "恍惚间", "仿佛看到", "梦里", "幻觉中"]
        has_flashback = any(ind in content for ind in flashback_indicators)

        for char in dead_chars:
            count = content.count(char)
            if count > 0 and not has_flashback:
                para_idx = self._find_para_of_text(content, char, paragraphs)
                issues.append(
                    GuardIssue(
                        guard_name=self.name,
                        severity=GuardSeverity.ERROR,
                        category="dead_character_appearance",
                        message=f"已死亡角色 '{char}' 在当前场景中出场",
                        paragraph_index=para_idx,
                        suggestion="确认是否为闪回/回忆场景，否则为角色设定矛盾",
                    )
                )
                score -= count * 20

        return max(0.0, score)

    def _analyze_character_mentions(
        self, content: str, characters: list[str], paragraphs: list[str], issues: list[GuardIssue]
    ) -> float:
        if not characters:
            return 80.0

        mentioned = [c for c in characters if c in content]
        mention_ratio = len(mentioned) / max(len(characters), 1)

        if len(paragraphs) > 20 and mention_ratio < 0.2:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.INFO,
                    category="low_character_density",
                    message=f"角色出场率低：仅 {len(mentioned)}/{len(characters)} 个角色出场",
                    suggestion="确认是否为故意设计，否则可增加角色互动",
                )
            )

        return 80.0 if mention_ratio > 0.1 else 60.0

    def _check_trait_consistency(
        self, content: str, character_traits: dict[str, list[str]], issues: list[GuardIssue]
    ) -> float:
        if not character_traits:
            return 80.0

        trait_conflicts = 0
        for char, traits in character_traits.items():
            if char not in content:
                continue

            opposite_pairs = [
                ("冷静", "冲动"),
                ("勇敢", "胆小"),
                ("聪明", "愚蠢"),
                ("善良", "邪恶"),
                ("正直", "狡诈"),
                ("开朗", "孤僻"),
            ]

            char_traits_lower = list(traits)
            for pos, neg in opposite_pairs:
                pos_in = any(pos in t for t in char_traits_lower)
                neg_in = any(neg in t for t in char_traits_lower)
                if pos_in and neg_in:
                    trait_conflicts += 1
                    issues.append(
                        GuardIssue(
                            guard_name=self.name,
                            severity=GuardSeverity.WARNING,
                            category="trait_contradiction",
                            message=f"角色 '{char}' 设定中存在矛盾特质：{pos}/{neg}",
                            suggestion="统一角色设定，避免特质矛盾",
                        )
                    )

        score = 100.0 - trait_conflicts * 20
        return max(40.0, score)

    def _find_para_of_text(self, content: str, text: str, paragraphs: list[str]) -> int:
        pos = content.find(text)
        if pos < 0:
            return 0
        current = 0
        for i, p in enumerate(paragraphs):
            p_start = content.find(p, current)
            if p_start >= 0 and p_start <= pos < p_start + len(p):
                return i
            if p_start >= 0:
                current = p_start + len(p)
        return 0
