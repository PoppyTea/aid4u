# s01e05_railway Module

## Purpose
Activates railway route X-01 through the hub's self-documenting, multi-step
`/verify` API (task="railway"). No LLM calls — `solve()` runs a fixed
protocol discovered from the API's own `help` action.

## Ownership
- `solution.py`: `RailwayTask` (`hub_name="railway"`) — `ROUTE` constant,
  `_call()` helper (submits one protocol step, raises on `ok: false`).
- `doc/`: course comments/demos/API help consulted while solving — not
  consumed by `solution.py` at runtime.
- `scripts/`: empty, reserved.

## Local Contracts
- Protocol is fixed: `help → reconfigure(route) → setstatus(route, RTOPEN)
  → save(route)`. Don't skip `help` even though the docs are already known
  here — it's cheap and the flag only appears after the exact sequence.
- `ROUTE = "X-01"` is a fixed value from the task's fabuła, not a
  per-user parameter — don't make it configurable or guess a different one.
- Rate-limit/outage resilience (503 + 429 with `retry_after` from the
  response body) lives in `HubClient.submit()`, not here — `solve()` calls
  `submit()` for every step (not just the final answer) and relies on that
  shared resilience. Don't add a second retry loop in this task.
- `RailwayTask._call()` MUST check `self.dry_run` before calling
  `self.hub.submit()` — only the *final* answer's submission is guarded by
  `BaseTask._submit()`; intermediate protocol steps called directly from
  `solve()` are not, and without this check `--dry-run` would silently
  mutate real hub state (reconfigure mode, route status). Caught in review
  on PR #51 (Qodo) — confirmed live before the fix (`--dry-run` was
  hitting `hub.ag3nts.org/verify` for real).

## Work Guidance
- If the protocol ever changes, re-run the `help` action live and diff
  against `doc/s01e05_api_help.md` before touching `solve()`.
- **Learning-mode teaching note:** when we revisit this task together in
  learning mode (course walkthrough, not efficiency mode), use it as the
  worked example for "how does an undocumented API map onto working code."
  Concretely: `help` response → `doc/s01e05_api_help.md` schema → the fixed
  action sequence in `solve()`/`_call()` → why resilience (503/429) had to
  live in the shared `HubClient.submit()` rather than duplicated per-task.
  Walk through `_call()`'s `ok: false` check and the dry-run guard above as
  a concrete case of "a review catches behavior a spec doesn't mention."

## Verification
- `uv run run.py solve s01e05 --dry-run` to inspect the final `save`
  answer before submitting — verified (2026-08-03, post-fix) that this
  makes zero real HTTP calls to the hub.
- Live-verified against the real hub (2026-08-03): full sequence
  (help → reconfigure → setstatus → save) returned `{FLG:COUNTRYROADS}`.

## Child DOX Index
- None.
