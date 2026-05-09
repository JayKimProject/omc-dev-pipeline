"""
Skill: string_utils
Common string manipulation helpers.
"""

import re


def slugify(text: str) -> str:
    """Convert text to lowercase-hyphenated slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)


def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    """Truncate text to max_len characters, appending suffix if cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def camel_to_snake(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


SKILL_META = {
    "name": "string_utils",
    "version": "1.0.0",
    "description": "Common string manipulation helpers",
    "author": "agent",
    "tags": ["strings", "utils"],
}
