"""
Developer Agent
===============
Reads a GitHub issue, implements the requested changes, commits them to a new
`agent/` branch, and opens a Pull Request.

Usage:
  python agents/developer.py --issue 7
  python agents/developer.py --issue 7 --repo owner/repo
"""

from __future__ import annotations

import argparse
import json
import os
import re
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


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def get_issue(number: int) -> dict:
    raw = gh("issue", "view", str(number), "--json", "number,title,body,labels")
    return json.loads(raw)


def current_branch() -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _list_files(pattern: str) -> str:
    result = subprocess.run(
        ["find", ".", "-name", pattern, "-not", "-path", "./.git/*"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() or "(no files matched)"


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        return f"Error: {exc}"


def _write_file(path: str, content: str) -> str:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return f"Written {len(content)} chars to {path}"


def _git_create_branch(name: str) -> str:
    branch = f"agent/{name}" if not name.startswith("agent/") else name
    git("checkout", "-b", branch)
    _state["branch"] = branch
    return f"Created and checked out: {branch}"


def _git_commit_and_push(message: str) -> str:
    git("add", "-A")
    try:
        git("commit", "-m", message)
    except RuntimeError:
        return "Nothing to commit"
    branch = _state.get("branch") or current_branch()
    git("push", "-u", "origin", branch)
    return f"Committed and pushed to {branch}"


def _create_pull_request(title: str, body: str, branch: str | None = None) -> str:
    branch = branch or _state.get("branch") or current_branch()
    result = subprocess.run(
        [GH, "pr", "create",
         "--title", title,
         "--body", body,
         "--head", branch,
         "--base", "main"],
        capture_output=True, text=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    _state["pr_url"] = output
    return output


# ---------------------------------------------------------------------------
# Agent state (mutable, shared across tool calls within one run)
# ---------------------------------------------------------------------------
_state: dict = {}

TOOLS: list[dict] = [
    {
        "name": "list_files",
        "description": "List repository files matching a glob pattern (e.g. '*.py', 'skills/*.py').",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from the repository.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file in the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "git_create_branch",
        "description": "Create and checkout a new branch. Use format: issue-{N}-{slug}. The 'agent/' prefix is added automatically.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "git_commit_and_push",
        "description": "Stage ALL changes, commit with the given message, and push the branch to origin.",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
    {
        "name": "create_pull_request",
        "description": "Open a GitHub Pull Request against main.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["title", "body"],
        },
    },
]

TOOL_MAP = {
    "list_files": lambda **kw: _list_files(**kw),
    "read_file": lambda **kw: _read_file(**kw),
    "write_file": lambda **kw: _write_file(**kw),
    "git_create_branch": lambda **kw: _git_create_branch(**kw),
    "git_commit_and_push": lambda **kw: _git_commit_and_push(**kw),
    "create_pull_request": lambda **kw: _create_pull_request(**kw),
}


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def run(issue_number: int) -> str:
    _state.clear()
    print(f"[Developer] Working on issue #{issue_number}")

    issue = get_issue(issue_number)
    agent_md = _read_file("AGENT.md")
    skill_md = _read_file("SKILL.md")

    system = f"""You are an AI Developer agent operating on a GitHub repository.

Your configuration (from AGENT.md):
{agent_md}

The skill specification (from SKILL.md):
{skill_md}

Workflow you MUST follow exactly:
1. Read relevant existing files to understand the codebase and code style.
2. Call git_create_branch with name "issue-{{number}}-{{short-slug}}".
3. Implement ALL changes described in the issue.
4. If the issue asks for a new skill: create skills/<name>.py AND update SKILL.md.
5. Call git_commit_and_push with a conventional commit message.
6. Call create_pull_request:
   - title: "feat|fix: <description> (closes #{issue['number']})"
   - body: include Summary, Changes Made, and Testing sections.

Do not stop until the PR is created.
"""

    user_msg = (
        f"Implement this GitHub issue:\n\n"
        f"**Issue #{issue['number']}: {issue['title']}**\n\n"
        f"{issue.get('body', '(no body)')}"
    )

    messages = [{"role": "user", "content": user_msg}]
    client = anthropic.Anthropic()

    for _ in range(40):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        for b in resp.content:
            if b.type == "text" and b.text.strip():
                print(f"[Developer] {b.text[:300]}")

        if resp.stop_reason == "end_turn" or not tool_uses:
            break

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for tu in tool_uses:
            print(f"[Developer] tool: {tu.name}({list(tu.input.keys())})")
            try:
                out = TOOL_MAP[tu.name](**tu.input)
            except Exception as exc:
                out = f"ERROR: {exc}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": str(out)[:4000],
            })
        messages.append({"role": "user", "content": tool_results})

    pr_url = _state.get("pr_url", "(no PR URL captured)")
    print(f"[Developer] Done — PR: {pr_url}")
    return pr_url


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Developer agent: issue → code → PR")
    parser.add_argument("--issue", type=int, required=True, help="GitHub issue number")
    args = parser.parse_args()
    run(args.issue)
