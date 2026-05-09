# SKILL.md — Skill Definitions

Each skill is a reusable, self-contained capability that can be assigned to agents.
Format inspired by SkillsMP (https://skillsmp.com) and the OMC paper's Talent spec.

A **skill** maps to one Python file in `skills/`. The file must export:
- A docstring at module level describing the skill
- One or more public functions (the skill's tools)
- A `SKILL_META` dict at the bottom with machine-readable metadata

---

## Skill: string_utils

**File:** `skills/string_utils.py`  
**Description:** Common string manipulation helpers.  
**Status:** stable

### Functions
| Name | Signature | Description |
|---|---|---|
| `slugify` | `(text: str) → str` | Convert text to lowercase-hyphenated slug |
| `truncate` | `(text: str, max_len: int, suffix: str) → str` | Truncate with ellipsis |
| `camel_to_snake` | `(name: str) → str` | Convert camelCase to snake_case |

### SKILL_META
```python
SKILL_META = {
    "name": "string_utils",
    "version": "1.0.0",
    "description": "Common string manipulation helpers",
    "author": "agent",
    "tags": ["strings", "utils"],
}
```

---

## Skill: file_scanner

**File:** `skills/file_scanner.py`  
**Description:** Scan a directory tree and return structured file information.  
**Status:** stable

### Functions
| Name | Signature | Description |
|---|---|---|
| `scan_directory` | `(root: str, extensions: list[str]) → list[dict]` | List files with metadata |
| `find_pattern` | `(root: str, pattern: str) → list[str]` | Glob search |
| `read_summary` | `(path: str, max_lines: int) → str` | Return first N lines of a file |

### SKILL_META
```python
SKILL_META = {
    "name": "file_scanner",
    "version": "1.0.0",
    "description": "Scan a directory tree and return structured file information",
    "author": "agent",
    "tags": ["files", "scanning", "utils"],
}
```

---

## Adding a New Skill

To add a new skill, open an issue labeled `agent-task` with:

```
Title: feat: add <skill_name> skill

Body:
## Skill: <skill_name>

**Description:** <what this skill does>

### Functions
- `function_name(args) → return_type` — description

### Acceptance criteria
- [ ] File created at skills/<skill_name>.py
- [ ] SKILL_META dict present
- [ ] Module-level docstring matches this spec
- [ ] All functions have type hints and docstrings
- [ ] Entry added to SKILL.md
```

The Developer agent will implement it, and the Reviewer agent will verify compliance
with this format before merging.
