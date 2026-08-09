# data/

## Purpose

Datasets and artifacts for course tasks (`tasks/sXXeYY/`). Read this before
touching anything under `data/` — some files are too large to read in full
and will blow out agent context if you `cat`/`Read` them whole.

Four subtrees, four lifecycles:
- `main_story/` — static datasets shipped with the course; never regenerated.
- `input/` — data fetched from hub.ag3nts.org at the start of a task, kept
  because it might matter to a *later* task (cross-episode continuity has
  bitten us before — see `tasks/AGENTS.md`). Committed. Own contract, see
  Child DOX Index.
- `output/` (no "s") — data *produced* while solving a task (derived/cleaned,
  not just re-saved raw input) that might matter to a later task. Committed.
  Sibling of `input/` — same "might be useful later" bar, opposite direction
  (in vs. produced). Own contract, see Child DOX Index.
- `run-history/` — every `solve()` run's submitted answer, named
  `sXXeYY-MMDD-HHMMSS-<slug>.<ext>`, written automatically by
  `BaseTask._save_output()`. Gitignored, disposable, **never** an input to
  another task — this is debug history ("what did we send and when"), not
  curated data. Don't confuse with `output/`.

**Rule of thumb:** if the answer to "would a later episode want this?" is
yes, it's `input/` or `output/`, gets a human-readable name, and is committed.
If it's "just so I can see what happened on this run," it's `run-history/`
(automatic) or `.cache/` (lives at the **repo root**, not under `core/` — implemented
by `../core/hub/cache.py` — pure dev-speed cache, hash-named, safe to `rm -rf` any
time, never holds anything not re-fetchable
from the hub).

## Ownership

Owned by the course task(s) that consume each file. Add or update the table
below whenever a **data** file is added, removed, or its role changes.
`run-history/` is append-only run history and isn't tracked file-by-file in
the table. `AGENTS.md`/DOX files themselves (e.g. `input/AGENTS.md`,
`output/AGENTS.md`) aren't data and don't get a row either — their contract
lives in the Child DOX Index above, not this table.

## Local Contracts

Sizes below are approximate on purpose — don't hand-maintain exact byte/line
counts, they drift and aren't the point. The point is knowing whether a file
is safe to read whole before you try.

| Path | Size (approx) | Purpose | Related task(s) | Described in | Safe to read in full? |
|---|---|---|---|---|---|
| `main_story/people.csv` | ~24k rows | Roster of people (name, surname, gender, birthDate, birthPlace, birthCountry, job) — input for candidate filtering | `s01e01_people` | `tasks/s01e01_people/solution.py` (`parse_csv`, `filter_candidates`, `format_answer`) | No — use `wc -l`, `head -n 5`, or `rg <pattern>` instead |

## Work Guidance

- Before reading a file under `data/`, check its row in the table above.
- If "Safe to read in full?" is No, use the safe commands listed instead of a full read (`head`, `tail`, `wc -l`, `rg`/`grep`). They're enough to understand shape and content without loading the whole file into context.
- New data file added? Add a row here in the same commit.

## Verification

(none yet)

## Child DOX Index

- `input/`: Doc trees fetched live from hub.ag3nts.org, one folder per task —
  fetch scripts, manifest format, NotebookLM mirroring.
- `output/`: Data produced while solving a task, kept because a later episode
  might need it — one folder per task, mirrors `input/`'s shape.
