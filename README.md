# OMC Dev Pipeline

An automated development pipeline where AI agents act as developer and reviewer — inspired by the [OMC paper](https://arxiv.org/abs/2604.22446) (Organising Heterogeneous Agents as a Real-World Company).

## How it works

```
GitHub Issue (labeled agent-task)
        │
        ▼
  Developer Agent ──► creates branch ──► writes code ──► opens PR
        │
        ▼
  Reviewer Agent  ──► reads diff ──► posts review ──► merges or closes
```

1. Add the `agent-task` label to any GitHub issue.
2. **Developer Agent** reads the issue, creates a branch (`agent/issue-N-slug`), implements the code, commits, and opens a PR.
3. **Reviewer Agent** reads the PR diff, posts a structured review comment, then either squash-merges (approved) or closes (rejected) the PR.

Both agents run automatically via GitHub Actions, or locally via `demo.py`.

## Repository layout

```
AGENT.md                  Agent role & tool specs
SKILL.md                  Skill library registry
agents/
  developer.py            Developer agent (issue → PR)
  reviewer.py             Reviewer agent (PR → merge/close)
skills/
  string_utils.py         Example skill: string helpers
  file_scanner.py         Example skill: directory scanner
.github/workflows/
  agent-develop.yml       Triggered on issues: labeled
  agent-review.yml        Triggered on pull_request: opened
demo.py                   Run the full pipeline locally
```

## Quick start

### GitHub Actions (fully automated)

1. Fork or clone this repo.
2. Add two repository secrets:
   - `ANTHROPIC_API_KEY` — your Anthropic key
   - `GH_PAT` — a GitHub personal access token with `repo` + `workflow` scopes
3. Create an issue and add the `agent-task` label → watch the pipeline run.

### Local demo

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python demo.py
```

`demo.py` creates a demo issue, runs the Developer agent, then runs the Reviewer agent end-to-end.

## Skill format

Each skill is a Python file in `skills/` with:

```python
"""Skill: <name>\n<description>"""

def function_name(arg: type) -> type:
    """One-line docstring."""
    ...

SKILL_META = {
    "name": "skill_name",
    "version": "1.0.0",
    "description": "...",
    "author": "agent",
    "tags": ["tag1"],
}
```

And a corresponding entry in `SKILL.md`. See [SKILL.md](SKILL.md) for the full spec.

## Acknowledgements

Architecture inspired by [*From Skills to Talent: Organising Heterogeneous Agents as a Real-World Company*](https://arxiv.org/abs/2604.22446).
