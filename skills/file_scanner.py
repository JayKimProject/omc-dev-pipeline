"""
Skill: file_scanner
Scan a directory tree and return structured file information.
"""

import os
import fnmatch
from pathlib import Path


def scan_directory(root: str, extensions: list[str] | None = None) -> list[dict]:
    """
    Recursively list files under root with metadata.

    Args:
        root:       Directory to scan.
        extensions: Optional filter, e.g. [".py", ".md"]. None = all files.

    Returns:
        List of dicts with keys: path, size, extension.
    """
    results = []
    for dirpath, _, filenames in os.walk(root):
        if ".git" in dirpath:
            continue
        for fname in filenames:
            ext = Path(fname).suffix
            if extensions and ext not in extensions:
                continue
            full = os.path.join(dirpath, fname)
            results.append({"path": full, "size": os.path.getsize(full), "extension": ext})
    return results


def find_pattern(root: str, pattern: str) -> list[str]:
    """
    Return file paths under root matching a glob pattern.

    Args:
        root:    Directory to search.
        pattern: Glob pattern, e.g. "*.py" or "skills/*.py".
    """
    return [
        os.path.join(dp, f)
        for dp, _, files in os.walk(root)
        if ".git" not in dp
        for f in files
        if fnmatch.fnmatch(f, pattern.split("/")[-1])
    ]


def read_summary(path: str, max_lines: int = 20) -> str:
    """Return the first max_lines lines of a file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = [next(fh) for _ in range(max_lines)]
        return "".join(lines)
    except StopIteration:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        return f"Error reading {path}: {exc}"


SKILL_META = {
    "name": "file_scanner",
    "version": "1.0.0",
    "description": "Scan a directory tree and return structured file information",
    "author": "agent",
    "tags": ["files", "scanning", "utils"],
}
