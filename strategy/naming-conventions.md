# Naming Conventions — aid4u
#
# SCOPE: All files and directories in this repository.
# AUTHORITY: This file is the single source of truth for naming.
#   When creating ANY new file, check here first.
# LANGUAGE: English only. No Polish characters in filenames.

---

## Core Rule

Two styles, two domains — no exceptions:

| Domain | Style | Example |
|---|---|---|
| Documentation / Strategy `.md` | `kebab-case` | `llm-selection.md` |
| Python source code `.py` | `snake_case` | `llm_adapter.py` |
| Root project standards | `UPPERCASE` | `CLAUDE.md`, `README.md` |
| Directories | `kebab-case` | `strategy/`, `skills/`, `agent-docs/` |

**Why the split?** `kebab-case` docs vs `snake_case` Python lets both agent and human
infer file type from style alone — no need to read the file to know what it is.

---

## Documentation Files (`.md`)

### Pattern

```
<topic>.md
<topic>-<subtopic>.md
```

### Rules

- All lowercase, words separated by hyphens
- English only — no Polish words, no accents
- Names are **nouns or noun phrases** describing the content, not the action
  - ✅ `llm-selection.md` (content: how to select LLMs)
  - ❌ `selecting-llms.md` (action verb)
  - ✅ `task-decomposition.md`
  - ❌ `how-to-decompose-tasks.md`
- No version suffix in filename (use git tags or `CHANGELOG.md`)
  - Exception: `<topic>-v{MAJOR}.md` **only** while old and new coexist during migration
  - Remove the version suffix once migration is complete
- No abbreviations unless universally known in the project domain
  - ✅ `llm-selection.md` (LLM is universal here)
  - ❌ `tdd-strat.md` → use `tdd-strategy.md`

### Examples

```
strategy/
├── llm-selection.md          ← kebab-case, bez wersji w nazwie
├── naming-conventions.md     ← ten plik
├── tasks/
│   └── workflow.md           ← jedno słowo też jest kebab-case
└── skills/
    ├── skill-activation.md
    └── skill-contracts.md
```

---

## Python Files (`.py`)

Standard PEP 8 — no changes to current practice.

```
snake_case.py           # modules
test_snake_case.py      # test files
__init__.py             # packages
```

---

## Root Project Standards (`UPPERCASE.md`)

Reserved for files read by agents, tools, or CI at the project root level.
Do not create new UPPERCASE files unless they are a widely recognized standard.

```
CLAUDE.md      ← Claude Code instructions (primary)
AGENTS.md      ← agent-agnostic instructions (Zed, Gemini CLI, etc.)
README.md      ← human-facing project overview
CHANGELOG.md   ← version history (if maintained)
```

---

## Directories

```
kebab-case/          # multi-word directories
single/              # single-word directories (no hyphen needed)
```

```
strategy/            ✅
strategy/tasks/      ✅
strategy/skills/     ✅
agent-docs/          ✅  (if ever created)
agentDocs/           ❌
agent_docs/          ❌
```

---

## Special Files (Tools and Agents)

| File | Convention | Reason |
|---|---|---|
| `SKILL.md` | `UPPERCASE` | Agent Skills open standard — do not rename |
| `.claude/settings.json` | lowercase | Tool config — do not rename |
| `CLAUDE_*.md` | `UPPERCASE_kebab` | CLAUDE.md imports via `@` — use sparingly |
| `pyrefly.toml`, `pyproject.toml` | lowercase | Tool config — do not rename |

---

## Agent Instructions

When creating a new file in this project:

1. Is it Python code? → `snake_case.py` in the appropriate module directory.
2. Is it a documentation/strategy file? → `kebab-case.md` in `strategy/` or relevant subdirectory.
3. Is it a root project standard? → Only UPPERCASE if it matches the table above.
4. Does it need a version? → Only add `-v{MAJOR}` if the old version must stay live.
5. Is it in English? → If not, translate the filename. Content can reference Polish terms.

When in doubt: `kebab-case.md` in the nearest relevant `strategy/` subdirectory.

---

## What NOT to do

```
❌ strategy_llm_v1.0.0.md        # snake_case + version in doc filename
❌ LlmSelection.md               # PascalCase for docs
❌ llmSelection.md               # camelCase for docs  
❌ Strategia_LLM.md              # Polish in filename
❌ llm-selection-final-v3.md     # "final" + version = chaos
❌ new-file-2.md                 # numbered duplicates
```
