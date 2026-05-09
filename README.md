# OMC Dev Pipeline

An automated development pipeline where AI agents act as developer and reviewer — inspired by the [OMC paper](https://arxiv.org/abs/2604.22446) (Organising Heterogeneous Agents as a Real-World Company).

## How it works

```
GitHub Issue  ──(label: agent-task)──►  Developer Agent
                                               │
                          creates branch + writes code + opens PR
                                               │
                                               ▼
                                        Reviewer Agent
                                               │
                          posts review comment + merges or closes PR
```

1. Add the `agent-task` label to any GitHub issue.
2. **Developer Agent** reads the issue, creates a branch (`agent/issue-N-slug`), implements the code, commits, and opens a PR.
3. **Reviewer Agent** reads the PR diff, posts a structured review comment, then either squash-merges (approved) or closes (rejected) the PR.

Both agents run automatically via GitHub Actions, or locally via `demo.py`.

---

## Setup (GitHub Actions)

### 1. Required secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (`sk-ant-...`) |
| `GH_PAT` | A GitHub Personal Access Token |

> **Why `GH_PAT`?** GitHub's built-in `GITHUB_TOKEN` cannot trigger downstream
> workflows. The Developer Agent pushes a branch and creates a PR; that PR must
> trigger the Reviewer Agent. A PAT with `repo` + `workflow` scopes makes this
> work.

**Creating a PAT:**
1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Repository access: this repo
3. Permissions: `Contents` (read/write), `Pull requests` (read/write), `Issues` (read/write), `Workflows` (read/write)

### 2. Create the `agent-task` label

Trigger the **Setup Labels** workflow once:

```
Actions → Setup Labels → Run workflow
```

Or run it locally:
```bash
gh workflow run setup-labels.yml
```

### 3. Trigger a run

Create any issue describing code to implement, then add the `agent-task` label.
The pipeline runs automatically:

```
Issue labeled  →  Agent Developer workflow  →  PR created
                                               →  Agent Reviewer workflow  →  merged ✅
```

---

## Local demo

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
# gh CLI must be authenticated: gh auth login
python demo.py
```

`demo.py` creates a demo issue ("feat: add math_utils skill"), runs the Developer
agent, waits, then runs the Reviewer agent — all in one terminal session.

---

## Repository layout

```
AGENT.md                         Agent role & tool specs
SKILL.md                         Skill library registry and format spec
agents/
  developer.py                   Developer agent  (issue → branch → PR)
  reviewer.py                    Reviewer agent   (PR → review → merge/close)
skills/
  string_utils.py                Skill: slugify, truncate, camel_to_snake
  file_scanner.py                Skill: scan_directory, find_pattern, read_summary
.github/workflows/
  agent-develop.yml              Triggered on issues: labeled (agent-task)
  agent-review.yml               Triggered on pull_request: opened from agent/ branch
  setup-labels.yml               One-time label bootstrap
demo.py                          Local end-to-end demo
```

---

## Skill format

Each skill is a Python file in `skills/` with:

```python
"""Skill: <name>
<one-line description>"""

def function_name(arg: type) -> type:
    """Docstring."""
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

---

## Acknowledgements

Architecture inspired by [*From Skills to Talent: Organising Heterogeneous Agents as a Real-World Company*](https://arxiv.org/abs/2604.22446).
