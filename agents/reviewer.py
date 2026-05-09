"""
Reviewer Agent
==============
Reads a GitHub PR diff, posts a structured code review comment, and either
squash-merges (approved) or closes (rejected) the PR.

Usage:
  python agents/reviewer.py --pr 3
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import anthropic

MODEL = "claude-sonnet-4-6"
GH = os.environ.get("GH_BIN", "gh")


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def gh(*args: str) -> str:
    result = subprocess.run([GH, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _get_pr_details(pr_number: int) -> str:
    raw = gh("pr", "view", str(pr_number),
             "--json", "number,title,body,headRefName,baseRefName,author,files")
    return raw


def _get_pr_diff(pr_number: int) -> str:
    result = subprocess.run(
        [GH, "pr", "diff", str(pr_number)],
        capture_output=True, text=True,
    )
    diff = result.stdout
    # Truncate very large diffs so we stay within context limits
    if len(diff) > 12_000:
        diff = diff[:12_000] + "\n\n... [diff truncated] ..."
    return diff or "(empty diff)"


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        return f"Error: {exc}"


def _post_review_comment(pr_number: int, body: str) -> str:
    gh("pr", "comment", str(pr_number), "--body", body)
    return f"Review comment posted on PR #{pr_number}"


def _merge_pr(pr_number: int, method: str = "squash") -> str:
    valid = {"squash", "merge", "rebase"}
    method = method if method in valid else "squash"
    result = subprocess.run(
        [GH, "pr", "merge", str(pr_number), f"--{method}", "--auto", "--delete-branch"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() or result.stderr.strip() or f"PR #{pr_number} merged ({method})"


def _close_pr(pr_number: int, reason: str = "") -> str:
    gh("pr", "close", str(pr_number), "--comment", reason or "Closed by reviewer agent.")
    return f"PR #{pr_number} closed"


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "get_pr_details",
        "description": "Get metadata for a PR: title, body, branch, changed files.",
        "input_schema": {
            "type": "object",
            "properties": {"pr_number": {"type": "integer"}},
            "required": ["pr_number"],
        },
    },
    {
        "name": "get_pr_diff",
        "description": "Get the unified diff for a PR (truncated at 12k chars).",
        "input_schema": {
            "type": "object",
            "properties": {"pr_number": {"type": "integer"}},
            "required": ["pr_number"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a repository file for additional context.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "post_review_comment",
        "description": "Post a review summary comment on the PR.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_number": {"type": "integer"},
                "body": {"type": "string", "description": "Markdown review body"},
            },
            "required": ["pr_number", "body"],
        },
    },
    {
        "name": "merge_pr",
        "description": "Squash-merge an approved PR and delete its branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_number": {"type": "integer"},
                "method": {
                    "type": "string",
                    "enum": ["squash", "merge", "rebase"],
                    "default": "squash",
                },
            },
            "required": ["pr_number"],
        },
    },
    {
        "name": "close_pr",
        "description": "Close a PR without merging (use when review fails).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_number": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["pr_number"],
        },
    },
]

TOOL_MAP = {
    "get_pr_details": lambda **kw: _get_pr_details(**kw),
    "get_pr_diff": lambda **kw: _get_pr_diff(**kw),
    "read_file": lambda **kw: _read_file(**kw),
    "post_review_comment": lambda **kw: _post_review_comment(**kw),
    "merge_pr": lambda **kw: _merge_pr(**kw),
    "close_pr": lambda **kw: _close_pr(**kw),
}


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def run(pr_number: int) -> str:
    print(f"[Reviewer] Reviewing PR #{pr_number}")

    agent_md = _read_file("AGENT.md")
    skill_md = _read_file("SKILL.md")

    system = f"""You are an AI Code Reviewer agent operating on a GitHub repository.

Your configuration (from AGENT.md):
{agent_md}

The skill specification (from SKILL.md):
{skill_md}

Review workflow you MUST follow:
1. Call get_pr_details to read the PR metadata and description.
2. Call get_pr_diff to read the code changes.
3. If needed, call read_file for additional context on unchanged files.
4. Evaluate the changes against these criteria:
   - Security: no secrets, no unsafe operations
   - Correctness: implementation matches the issue requirements in the PR body
   - Style: matches existing code conventions
   - Skill format: if a skill was added, verify it matches SKILL.md spec exactly
     (module docstring, type hints, SKILL_META dict, SKILL.md entry updated)
5. Call post_review_comment with a structured review:

   ## Review: PR #{{N}} — {{verdict}}

   **Verdict:** ✅ APPROVED / ❌ REJECTED

   ### Findings
   - finding 1
   - finding 2

   ### Decision
   <reason>

6. If APPROVED: call merge_pr to squash-merge.
   If REJECTED: call close_pr with a clear reason.

Do not stop until you have posted the review comment AND either merged or closed the PR.
"""

    messages = [{"role": "user", "content": f"Please review PR #{pr_number}."}]
    client = anthropic.Anthropic()

    for _ in range(30):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        for b in resp.content:
            if b.type == "text" and b.text.strip():
                print(f"[Reviewer] {b.text[:300]}")

        if resp.stop_reason == "end_turn" or not tool_uses:
            break

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for tu in tool_uses:
            print(f"[Reviewer] tool: {tu.name}({list(tu.input.keys())})")
            try:
                out = TOOL_MAP[tu.name](**tu.input)
            except Exception as exc:
                out = f"ERROR: {exc}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": str(out)[:6000],
            })
        messages.append({"role": "user", "content": tool_results})

    print(f"[Reviewer] Done with PR #{pr_number}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reviewer agent: PR → review → merge/close")
    parser.add_argument("--pr", type=int, required=True, help="GitHub PR number")
    args = parser.parse_args()
    run(args.pr)
