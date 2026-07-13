import os
import re
from dataclasses import dataclass

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


@dataclass
class TemplateInfo:
    name: str
    purpose: str = ""
    estimated_tokens: int = 0
    has_system: bool = False
    has_user: bool = True
    output_format: str = "text"


class PromptManager:
    def __init__(self, prompts_dir: str = ""):
        self.prompts_dir = prompts_dir
        self._cache: dict[str, dict] = {}
        self._info_cache: dict[str, TemplateInfo] = {}

    def render(self, template_name: str, context: dict = None) -> str:
        if context is None:
            context = {}
        template_data = self._load_template(template_name)
        user_prompt = (
            template_data.get("user_prompt", "") or template_data.get("user", "") or template_data.get("content", "")
        )
        system_prompt = template_data.get("system_prompt", "") or template_data.get("system", "")

        user_prompt = self._replace_variables(user_prompt, context)
        if system_prompt:
            system_prompt = self._replace_variables(system_prompt, context)
            return system_prompt + "\n\n" + user_prompt
        return user_prompt

    def render_messages(self, template_name: str, context: dict = None) -> list[dict[str, str]]:
        if context is None:
            context = {}
        template_data = self._load_template(template_name)
        user_prompt = (
            template_data.get("user_prompt", "") or template_data.get("user", "") or template_data.get("content", "")
        )
        system_prompt = template_data.get("system_prompt", "") or template_data.get("system", "")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": self._replace_variables(system_prompt, context)})
        if user_prompt:
            messages.append({"role": "user", "content": self._replace_variables(user_prompt, context)})
        return messages

    def get_template_info(self, template_name: str) -> TemplateInfo:
        if template_name in self._info_cache:
            return self._info_cache[template_name]

        template_data = self._load_template(template_name)
        system_prompt = template_data.get("system_prompt", "") or template_data.get("system", "")
        user_prompt = (
            template_data.get("user_prompt", "") or template_data.get("user", "") or template_data.get("content", "")
        )

        output_format = template_data.get("output_format", "text")
        purpose = template_data.get("purpose", "")
        estimated = (len(system_prompt) + len(user_prompt)) // 2

        info = TemplateInfo(
            name=template_name,
            purpose=purpose,
            estimated_tokens=estimated,
            has_system=bool(system_prompt),
            has_user=bool(user_prompt),
            output_format=output_format,
        )
        self._info_cache[template_name] = info
        return info

    def list_templates(self) -> list[str]:
        if not self.prompts_dir or not os.path.exists(self.prompts_dir):
            return []
        templates = []
        for f in os.listdir(self.prompts_dir):
            if f.endswith(".yaml") or f.endswith(".yml"):
                templates.append(os.path.splitext(f)[0])
        return sorted(templates)

    def _load_template(self, template_name: str) -> dict:
        if template_name in self._cache:
            return self._cache[template_name]

        template_path = os.path.join(self.prompts_dir, f"{template_name}.yaml")
        if os.path.exists(template_path) and _HAS_YAML:
            with open(template_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                data = {"content": str(data)}
        elif os.path.exists(template_path) and not _HAS_YAML:
            data = self._load_simple_yaml(template_path)
        else:
            data = self._get_default_template(template_name)

        self._cache[template_name] = data
        return data

    def _replace_variables(self, text: str, variables: dict) -> str:
        def replacer(match):
            key = match.group(1)
            val = variables.get(key, match.group(0))
            return str(val)

        result = re.sub(r"\{\{(\w+)\}\}", replacer, text)

        def safe_replacer(match):
            key = match.group(1)
            val = variables.get(key, match.group(0))
            return str(val)

        result = re.sub(r"\$\{(\w+)\}", safe_replacer, result)

        return result

    def _load_simple_yaml(self, file_path: str) -> dict:
        result: dict[str, str] = {}
        current_key: str | None = None
        current_value: list[str] = []
        in_multiline = False

        with open(file_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.rstrip("\n")

                if in_multiline:
                    if stripped.startswith("  ") or stripped == "":
                        current_value.append(stripped[2:] if stripped.startswith("  ") else "")
                        continue
                    else:
                        if current_key is not None:
                            result[current_key] = "\n".join(current_value).rstrip()
                        in_multiline = False
                        current_key = None
                        current_value = []

                if ":" in stripped and not stripped.startswith(" "):
                    key, _, value = stripped.partition(":")
                    key = key.strip()
                    value = value.strip()

                    if value == "|":
                        current_key = key
                        current_value = []
                        in_multiline = True
                    else:
                        result[key] = value.strip('"').strip("'")

        if in_multiline and current_key is not None:
            result[current_key] = "\n".join(current_value).rstrip()

        return result

    def _get_default_template(self, template_name: str) -> dict:
        defaults = {
            "chapter-outline": {
                "system_prompt": """你是一位资深的网络小说编辑，擅长构思精彩的章节大纲。
你精通情节设计、节奏把控和悬念设置，能够根据已有设定创作出逻辑自洽、引人入胜的章节大纲。
请严格按照要求的格式输出，不要添加额外的解释或说明。""",
                "user_prompt": """请根据以下信息创作本章的详细大纲：

【小说信息】
标题：{{novel_title}}
类型：{{novel_genre}}
核心设定：{{novel_premise}}

【人物设定】
{{characters}}

【世界观设定】
{{world_settings}}

【前文概要】
{{previous_summary}}

【本章信息】
章节编号：第 {{chapter_number}} 章
章节标题：{{chapter_title}}

请输出本章的详细大纲，包含以下内容：
1. 核心事件：本章主要发生了什么
2. 主要冲突：本章的核心矛盾是什么
3. 爽点/亮点：读者最期待的部分
4. 人物发展：人物有什么变化或成长
5. 章末钩子：结尾留下什么悬念

请使用 Markdown 格式输出，确保情节连贯、节奏合理、符合人物设定和世界观。""",
            },
            "chapter-content": {
                "system_prompt": """你是一位顶尖的网络小说作家，文笔生动，擅长刻画人物和营造氛围。
你精通各种写作技巧，能够写出情节扣人心弦、人物鲜活立体、细节丰富饱满的高质量内容。

写作要求：
1. 多用动作、对话、环境描写展示人物情绪，避免直接说出情绪词（如"他很愤怒""她感到悲伤"等）
2. 避免元话语（如"只见""却见""这时""突然"等），直接呈现场景
3. 控制副词使用，用具体动作替代"非常""十分""慢慢地"等副词
4. 对话要自然，符合人物身份和性格，避免超长独白
5. 情节要连贯，前后呼应，遵守世界观设定和人物设定
6. 只输出正文内容，不要解释、说明或思考过程""",
                "user_prompt": """请根据以下信息创作本章正文：

【小说信息】
标题：{{novel_title}}
类型：{{novel_genre}}
核心设定：{{novel_premise}}

【人物设定】
{{characters}}

【世界观设定】
{{world_settings}}

【前文概要】
{{previous_summary}}

【本章规划】
章节编号：第 {{chapter_number}} 章
章节标题：{{chapter_title}}
本章大纲：
{{chapter_outline}}

【字数要求】
约 {{target_words}} 字左右

请创作本章正文内容，要求：
- 情节连贯，节奏得当
- 人物言行符合设定
- 描写生动，细节饱满
- 对话自然，推动情节
- 结尾留有悬念
- 只输出正文，不要任何额外说明""",
            },
            "content-review": {
                "system_prompt": """你是一位资深的文学编辑和质量审查员，眼光独到，评判公正。
你精通小说创作的各项技法，能够从多个维度对作品进行专业评估。
你善于发现问题并给出切实可行的改进建议。
你的评判标准严格但客观，既不会吹毛求疵，也不会敷衍了事。
输出必须严格遵循 JSON 格式，不得包含任何额外的解释或说明文字。""",
                "user_prompt": """请审查以下章节内容的质量：

【小说信息】
标题：{{novel_title}}
类型：{{novel_genre}}

【人物设定】
{{characters}}

【世界观设定】
{{world_settings}}

【前文概要】
{{previous_summary}}

【本章章纲】
{{chapter_outline}}

【章节内容】
{{chapter_content}}

请从以下维度进行审查评分（0-100分）：
1. 情节连贯性：情节是否流畅，前后是否呼应，节奏是否得当
2. 人物一致性：人物言行是否符合设定，性格是否统一
3. 设定一致性：是否遵守世界观设定，有无前后矛盾
4. 文笔流畅度：文字是否优美，描写是否生动，对话是否自然

输出 JSON 格式，包含以下字段：
- total_score: 总分（0-100）
- grade: 等级（S/A/B/C/D）
- dimension_scores: 各维度分数，包含 plot_coherence, character_consistency, setting_consistency, writing_quality
- issues: 问题列表，每个包含 dimension(维度), description(描述), severity(严重程度: high/medium/low)
- suggestions: 改进建议列表
- overall_comment: 总体评价""",
            },
        }
        return defaults.get(template_name, {"content": ""})
