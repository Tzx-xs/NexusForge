from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import cast

try:
    from json_repair import repair_json

    _HAS_JSON_REPAIR = True
except ImportError:
    _HAS_JSON_REPAIR = False


@dataclass
class OutlineData:
    title: str = ""
    core_event: str = ""
    conflict: str = ""
    cool_point: str = ""
    character_development: str = ""
    ending_hook: str = ""
    raw_text: str = ""
    sections: dict[str, str] = field(default_factory=dict)


class OutputParser:
    def parse_json(self, text: str) -> dict:
        if not text:
            return {}

        try:
            return cast(dict, json.loads(text))
        except (json.JSONDecodeError, Exception):
            pass

        if _HAS_JSON_REPAIR:
            try:
                repaired = repair_json(text)
                return cast(dict, json.loads(repaired))
            except (json.JSONDecodeError, Exception):
                pass

        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return cast(dict, json.loads(json_match.group()))
            except (json.JSONDecodeError, Exception):
                pass

        raise ValueError(f"JSON 解析失败，无法从文本中提取有效 JSON: {text[:100]}...")

    def parse_markdown_outline(self, text: str) -> OutlineData:
        if not text:
            return OutlineData()

        text = text.strip()
        sections = {}

        lines = text.split("\n")
        current_key = None
        current_content = []
        rest = ""

        for line in lines:
            stripped = line.strip()
            is_heading = False
            heading_text = None
            rest = ""

            if stripped.startswith("### "):
                heading_text = stripped[4:].strip()
                is_heading = True
            elif stripped.startswith("## "):
                heading_text = stripped[3:].strip()
                is_heading = True
            elif stripped.startswith("# "):
                heading_text = stripped[2:].strip()
                is_heading = True

            colon_match = re.match(r"^(.+?)[：:]\s*(.*)$", stripped)
            if colon_match and not is_heading:
                heading_text = colon_match.group(1).strip()
                rest = colon_match.group(2).strip()
                if heading_text and len(heading_text) < 20:
                    is_heading = True
                    if rest:
                        current_content = [rest]
                    else:
                        current_content = []

            if is_heading and heading_text:
                if current_key and current_content:
                    sections[current_key] = "\n".join(current_content).strip()
                current_key = heading_text
                if not rest or not colon_match:
                    current_content = []
                continue

            if current_key:
                current_content.append(line)

        if current_key and current_content:
            sections[current_key] = "\n".join(current_content).strip()

        keyword_map = {
            "core_event": ["核心事件", "主线事件", "主要事件", "本章核心"],
            "conflict": ["主要冲突", "核心冲突", "主要矛盾", "冲突点"],
            "cool_point": ["爽点", "亮点", "高潮", "精彩看点", "爽点/亮点"],
            "character_development": ["人物发展", "人物成长", "人物变化", "角色发展"],
            "ending_hook": ["章末钩子", "结尾悬念", "悬念", "钩子", "章末悬念"],
        }

        result = {}
        for key, keywords in keyword_map.items():
            for section_name, content in sections.items():
                for kw in keywords:
                    if kw in section_name:
                        result[key] = content.strip()
                        break
                if key in result:
                    break

        title = ""
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        return OutlineData(
            title=title,
            core_event=result.get("core_event", ""),
            conflict=result.get("conflict", ""),
            cool_point=result.get("cool_point", ""),
            character_development=result.get("character_development", ""),
            ending_hook=result.get("ending_hook", ""),
            raw_text=text,
            sections=sections,
        )

    def extract_content(self, text: str) -> str:
        if not text:
            return ""

        text = text.strip()

        lines = text.split("\n")
        filtered_lines = []
        in_body = False

        for line in lines:
            stripped = line.strip()
            if not in_body:
                is_header = any(
                    re.match(p, stripped)
                    for p in [
                        r"^好的",
                        r"^以下",
                        r"^这是",
                        r"^我来",
                        r"^开始",
                    ]
                )
                if is_header:
                    continue
                if stripped == "":
                    continue
                in_body = True
            filtered_lines.append(line)

        result = "\n".join(filtered_lines).strip()

        tail_patterns = [
            r"\n\s*---\s*\n.*$",
            r"\n\s*以上是.*$",
            r"\n\s*希望.*$",
            r"\n\s*如果.*$",
        ]
        for p in tail_patterns:
            result = re.sub(p, "", result, flags=re.DOTALL)

        return result.strip()

    def safe_parse_json(self, text: str, default: dict | None = None) -> dict:
        try:
            return self.parse_json(text)
        except (ValueError, Exception):
            return default or {}
