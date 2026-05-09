"""
Demo: Full Agent Development Pipeline
======================================

Creates a GitHub issue, runs the Developer agent to implement it, then
runs the Reviewer agent to evaluate and merge the PR — all locally.

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python demo.py

What happens:
  1. Creates a GitHub issue: "feat: add math_utils skill"
  2. Developer agent: reads issue → creates branch → writes skills/math_utils.py
     + updates SKILL.md → commits → pushes → opens PR
  3. Reviewer agent: reads PR diff → posts review comment → merges (if approved)
"""

import os
import subprocess
import sys
import time

DIVIDER = "=" * 65

DEMO_ISSUE_TITLE = "feat: add math_utils skill"
DEMO_ISSUE_BODY = """\
## Skill: math_utils

**Description:** Common numeric and math helper functions.

### Functions

- `clamp(value, min_val, max_val) → float` — clamp a value between min and max
- `percentage(part, total) → float` — return (part/total)*100, safe division
- `moving_average(values, window) → list[float]` — simple moving average

### Acceptance Criteria

- [ ] File created at `skills/math_utils.py`
- [ ] Module-level docstring: `Skill: math_utils\\nCommon numeric and math helper functions.`
- [ ] All three functions implemented with type hints and docstrings
- [ ] `SKILL_META` dict present with name, version, description, author, tags
- [ ] Entry added to `SKILL.md` following the existing format
- [ ] All functions handle edge cases (division by zero, empty list)
"""

GH = os.environ.get("GH_BIN", "gh")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kwargs)


def gh_run(*args: str) -> str:
    result = subprocess.run([GH, *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [WARN] gh {' '.join(args)}: {result.stderr.strip()}", file=sys.stderr)
    return result.stdout.strip()


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    print(DIVIDER)
    print("  OMC Dev Pipeline — Local Demo")
    print(DIVIDER)

    # ------------------------------------------------------------------
    # Step 1: Create the demo issue
    # ------------------------------------------------------------------
    print("\n[Step 1] Creating demo GitHub issue...")
    issue_url = gh_run(
        "issue", "create",
        "--title", DEMO_ISSUE_TITLE,
        "--body", DEMO_ISSUE_BODY,
        "--label", "agent-task",
    )
    print(f"  Issue created: {issue_url}")

    # Extract issue number from URL (e.g. https://github.com/owner/repo/issues/7)
    issue_number = int(issue_url.rstrip("/").split("/")[-1])
    print(f"  Issue number: #{issue_number}")

    # ------------------------------------------------------------------
    # Step 2: Developer agent
    # ------------------------------------------------------------------
    print(f"\n[Step 2] Running Developer agent on issue #{issue_number}...")
    print(DIVIDER)

    from agents.developer import run as developer_run
    pr_url = developer_run(issue_number)

    print(DIVIDER)
    print(f"  PR created: {pr_url}")

    # Extract PR number
    if pr_url and "/pull/" in pr_url:
        pr_number = int(pr_url.rstrip("/").split("/")[-1])
    else:
        # Fallback: look up the most recent open PR from an agent/ branch
        raw = gh_run("pr", "list", "--json", "number,headRefName", "--limit", "5")
        import json
        prs = json.loads(raw) if raw.startswith("[") else []
        agent_prs = [p for p in prs if p["headRefName"].startswith("agent/")]
        if not agent_prs:
            print("  [WARN] Could not determine PR number. Run reviewer manually.")
            sys.exit(0)
        pr_number = agent_prs[0]["number"]

    print(f"  PR number: #{pr_number}")

    # ------------------------------------------------------------------
    # Step 3: Reviewer agent
    # ------------------------------------------------------------------
    print(f"\n[Step 3] Running Reviewer agent on PR #{pr_number}...")
    print(DIVIDER)

    # Brief pause so GitHub indexes the PR
    time.sleep(3)

    from agents.reviewer import run as reviewer_run
    reviewer_run(pr_number)

    print(DIVIDER)
    print("\n  Demo complete!")
    print(f"  Issue : {issue_url}")
    print(f"  PR    : {pr_url}")
    print(f"\n  Check the repository for the merged skill and updated SKILL.md.")


if __name__ == "__main__":
    main()
