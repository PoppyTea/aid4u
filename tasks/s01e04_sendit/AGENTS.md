# s01e04_sendit Module

## Purpose
SPK (System Przesyłek Konduktorskich) shipping declaration — a fully
deterministic task, no LLM calls. `solve()` builds a fixed-format text
declaration and submits it to `/verify`.

## Ownership
- `solution.py`: `SendItTask` (`hub_name="sendit"`) — declaration constants,
  `calculate_wdp()`, `build_declaration()`.
- `doc/`: course comments/demos consulted while solving — not consumed by
  `solution.py` at runtime.
- Reference material this task depends on lives in
  `data/input/s01e04_sendit/` (see that folder's own AGENTS.md), not here.

## Local Contracts
- Declaration field values and formatting (headers, `---`/`===` separators,
  field order) MUST match `data/input/s01e04_sendit/system-przesylek-konduktorskich/zalacznik-E.md`
  exactly — the hub verifies both content and format.
- `TRASA` stays `X-01` even though it's a disabled route — the task
  explicitly says to ignore that status.

## Work Guidance
- Route/fee/category lookups: use
  `data/input/s01e04_sendit/spk-network-graph.md`, not `zalacznik-F.md`
  (known-inaccurate ASCII schematic — see that folder's AGENTS.md).

## Verification
- `uv run run.py solve s01e04 --dry-run` to inspect the built declaration
  before submitting.
- Live-verified against the real hub (2026-08-02): submitted declaration
  returned `{FLG:WISDOM}`.

## Child DOX Index
- None.
