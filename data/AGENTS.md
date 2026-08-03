# data/

## Purpose

Datasets and artifacts for course tasks (`tasks/sXXeYY/`). Read this before
touching anything under `data/` — some files are too large to read in full
and will blow out agent context if you `cat`/`Read` them whole.

Three subtrees, three lifecycles:
- `main_story/` — static datasets shipped with the course; never regenerated.
- `input/` — reference doc trees fetched live from hub.ag3nts.org; regenerable
  by re-running the task's fetch script. Own contract, see Child DOX Index.
- `outputs/` — run artifacts written by solved tasks, named
  `sXXeYY-MMDD-HHMMSS-<slug>.<ext>`. Disposable; never an input to another task.

## Ownership

Owned by the course task(s) that consume each file. Add or update the table
below whenever a file is added, removed, or its role changes. `outputs/` is
append-only run history and isn't tracked file-by-file in the table.

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
