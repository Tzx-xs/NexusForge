import os
import re
from typing import Any

from domain.shared.exceptions import PromptNotFoundException

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


class PromptManager:
    def __init__(self, prompts_dir: str) -> None:
        self.prompts_dir = prompts_dir
        self._cache: dict[str, dict] = {}

    def get_prompt(self, name: str) -> dict:
        if name in self._cache:
            return self._cache[name]

        file_path = os.path.join(self.prompts_dir, f"{name}.yaml")
        if not os.path.exists(file_path):
            raise PromptNotFoundException(name)

        if _HAS_YAML:
            with open(file_path, encoding="utf-8") as f:
                data: dict = yaml.safe_load(f)
        else:
            data = self._load_simple_yaml(file_path)

        self._cache[name] = data
        return data

    def format_prompt(self, name: str, **kwargs: Any) -> tuple[str, str]:
        prompt_data = self.get_prompt(name)
        system_prompt = prompt_data.get("system_prompt", "")
        user_prompt = prompt_data.get("user_prompt", "")

        system_prompt = self._replace_variables(system_prompt, kwargs)
        user_prompt = self._replace_variables(user_prompt, kwargs)

        return system_prompt, user_prompt

    def _replace_variables(self, text: str, variables: dict[str, Any]) -> str:
        def replacer(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables.get(key, match.group(0)))

        return re.sub(r"\{\{(\w+)\}\}", replacer, text)

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
