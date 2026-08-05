# data/input/

## Purpose

Raw reference material fetched live from hub.ag3nts.org for tasks whose input
isn't a single API payload but a small document tree (e.g. `s01e04_sendit`'s
SPK docs, cross-linked via `include file="..."` references). Sibling of
`../main_story/` (static datasets shipped with the course), `../output/`
(data produced rather than fetched — mirror image of this folder), and
`../run-history/` (disposable per-run audit trail) — see `../AGENTS.md`.

## Ownership

Owned by the course task(s) that consume each subfolder. One subfolder per
`sXXeYY`.

## Local Contracts

- Every `sXXeYY/` subfolder, and every content folder nested inside it, is a
  Python package (`__init__.py`, empty) — even when the folder name itself
  isn't a valid Python identifier (e.g. `system-przesylek-konduktorskich`).
- Fetch scripts live colocated with the data they populate (e.g.
  `s01e04_sendit/fetch_spk_files.py`), not under `scripts/` — `scripts/` is
  for repo-wide utilities, not single-task data acquisition.
- Manifest files (e.g. `SPK_files_list.csv`) are plain newline-delimited file
  paths, not real CSV — one path per line, no header, no delimiter. Read into
  a `set[Path]` to dedupe; paths may include subfolders.
- All hub.ag3nts.org access goes through `core.hub.client.HubClient` (see
  `../../core/AGENTS.md`) — never raw `httpx` in these scripts.
- Downloaded docs also get pushed into a matching NotebookLM notebook (one
  notebook per task, named `LLM_sXXeYY - <opis>`) for course-comment lookup.
- Derived artifacts (renders, extracted graphs, cleaned-up transcriptions) may
  sit next to the fetched tree but never inside the fetch target folder, and
  carry English kebab-case names — so `sXXeYY/spk-network-graph.md`, not
  `sXXeYY/system-przesylek-konduktorskich/`. Anything the fetch script writes
  is disposable; anything derived is not.

## Work Guidance

- When a task needs a linked document tree, reuse the BFS include-resolution
  pattern from `s01e04_sendit/fetch_spk_files.py` (download → regex-scan for
  more refs → append unseen refs to the manifest → repeat until the queue
  drains) instead of reinventing it.

## Verification

(none yet)

## Child DOX Index

- `s01e04_sendit/`: SPK (System Przesyłek Konduktorskich) docs — fetched via
  `fetch_spk_files.py`, mirrored into NotebookLM notebook
  `LLM_s01e04 - dokumentacja Systemu Przesyłek Konduktorskich`
  (id `3020c5f5-a957-4ce0-9948-deece15e0edd`). Route graph: use
  `spk-network-graph.md` (built from the `index.md` route tables), **not**
  `zalacznik-F.md` — that ASCII schematic omits 6 routes and mislabels 9.
- `s01e05_railway/`: package placeholder only, no content fetched yet.
