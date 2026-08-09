# Core Module

## Purpose
Contains the architectural heart of the system: LLM clients, task management bases, observability instrumentation, and hub connectivity.

## Ownership
- `core/llm/`: LLM integration and adapter logic.
- `core/hub/`: Data acquisition and caching.
- `core/tasks/`: Base classes for task registration.
- `core/observability/`: Instrumentation and tracing decorators.
- `core/runtime/`: Kill switch (process-group panic, graceful stop, run budgets).

## Local Contracts
- All external API interactions MUST go through `core/llm/client.py`.
  - **Exception:** `core/llm/native_tool_*.py` (Anthropic native tools — web_search,
    code_execution, bash, text_editor) call `anthropic.Anthropic` directly instead of
    going through `LLMClient`. These aren't portable across providers, so they're a
    deliberate, narrow exception — not a precedent for other bypasses.
- Any new task MUST inherit from `core/tasks/base.py` and be decorated with `@task`.
- `BaseTask._save_output()` writes every `solve()` run's submitted answer to
  `data/run-history/` (`sXXeYY-MMDD-HHMMSS-<slug>.<ext>`), automatically, after
  every run — disposable per-run audit trail, gitignored, never an input to
  another task. Don't confuse with `data/output/` (no "s"), which is committed
  and holds data deliberately kept because a later episode might need it — see
  `data/AGENTS.md` for the full four-way split.
- `HubClient.submit()` retries transparently on `/verify` 503 (simulated outage) and
  429 (rate limit) — for 429 it waits on the `retry_after` field from the JSON
  response body (the hub does not set a standard `Retry-After` header). It raises
  `RuntimeError` after exhausting attempts. Callers can invoke `submit()` more than
  once per task run for multi-step hub protocols (e.g. `s01e05_railway`), not just
  for the final answer — each call gets the same resilience.
- `HubClient.post_api()` (used for `/api/*` endpoints, e.g. `zmail`) retries on 429 and
  5xx/transport errors with exponential backoff (`tenacity`, 6 attempts, 3-30s). Added
  2026-08-07 after `s02e04_mailbox` hit real rate limiting on `/api/zmail`
  (`{"code": -9999, "message": "Za często wykonujesz zapytania. Zwolnij."}`) even though
  the task's own docs never mentioned one — unlike `/verify`, these endpoints don't return
  a `retry_after` field, so the backoff here is blind/exponential, not server-directed.
  Other 4xx (e.g. an unknown action name) still propagate immediately — only 429 is treated
  as transient.
- **Kill switch (`core/runtime/killswitch.py`) — three layers, none may depend on the
  agent's cooperation to work:**
  - **Layer 0 (OS-level, guaranteed):** `BaseTask.run()` calls `start_run()`, which puts
    the process in its own process group (`os.setsid()`) and writes the PGID to
    `.run/current.pgid`. `scripts/panic.sh` (pure bash, zero Python/venv dependency —
    must work even when the environment is broken) sends SIGTERM then SIGKILL to
    `-PGID` (the leading `-` kills the whole group, not just the leader, so child
    processes — e.g. a shell command spawned by a s03e02-style tool — die too).
    Verified with a real subprocess-group test, not just a mock:
    `tests/core/runtime/test_killswitch.py::TestPanicScriptKillsEntireProcessGroup`.
  - **Layer 1 (cooperative, graceful):** `.run/STOP` sentinel file. `check_abort()`
    raises `AbortRun` when it exists — call it at safe checkpoints (agent-loop
    iteration start, before each tool call, before `hub.submit()`). `BaseTask.run()`
    catches `AbortRun` and returns cleanly (flushes Langfuse, no traceback spam).
    `run.py panic --graceful` writes the sentinel.
  - **Layer 2 (budgets, self-triggering):** per-run wall-clock (`start_run(max_seconds=...)`,
    exposed as `solve --max-seconds`, checked automatically inside `check_abort()`) and
    per-call tool-result size (`truncate_tool_result()`, applied in
    `LLMClient.run_agent_loop()` — corrects a single call, does NOT abort the run).
    Cost/token budget is NOT implemented yet (would need `CostTrackMiddleware` to expose
    a running total mid-run, not just at the end) — noted as a gap in `killswitch.py`'s
    module docstring, not silently absent.
  - Any caller that wraps a tool executor's exceptions (as `run_agent_loop` does) MUST
    re-raise `AbortRun` specifically, not swallow it into a generic error string — it's
    a kill signal, not a tool failure.
- Both `Config._from_keyring()` and `SecretsManager.get()`/`list()` MUST read the
  system keyring only through `core.secrets._keyring_get_with_timeout()`, never
  `keyring.get_password()` directly. Headless/VPS environments without a D-Bus
  secret service can make `keyring.get_password()` block forever instead of
  raising (hit 2026-08-05 — hung the whole `uv run pytest` at collection time via
  `setup_observability()` → `cfg.logfire_token`). The helper bounds each call to
  `_KEYRING_TIMEOUT_SECONDS` (2s) on a daemon thread, and trips a circuit breaker
  (`_KEYRING_BACKOFF_SECONDS`, 5min) after the first timeout so a permanently
  broken keyring can't accumulate one abandoned thread per call — Python has no
  safe way to kill a blocked thread, so every avoided call matters.

## Work Guidance
- Follow the Adapter pattern for new LLM providers.
- Maintain consistent interface usage across adapters.
- Anthropic-only native tools (`core/llm/native_tool_*.py`) are standalone functions,
  not `AnthropicAdapter` methods — each builds its own `anthropic.Anthropic(api_key=...)`
  client rather than reaching into adapter internals. This keeps every native-tool module
  a net-new file with zero shared-code edits, so independent tool branches (see root
  AGENTS.md batch implementation workflow) never conflict regardless of merge order.

## Verification
- Run tests in `tests/core/` before committing.

## Child DOX Index
- None.
