# Core Module

## Purpose
Contains the architectural heart of the system: LLM clients, task management bases, observability instrumentation, and hub connectivity.

## Ownership
- `core/llm/`: LLM integration and adapter logic.
- `core/hub/`: Data acquisition and caching.
- `core/tasks/`: Base classes for task registration.
- `core/observability/`: Instrumentation, tracing decorators, prompt registry
  (`prompts.py` — code→Langfuse one-way sync, see `strategy/observability.md`).
- `core/runtime/`: Kill switch (process-group panic, graceful stop, run budgets).
- `core/net.py`: Content validation for anything fetched over the network
  (soft-404 detection) — independent of `HubClient`, not hub-specific.

## Local Contracts
- All external **LLM provider** API interactions MUST go through `core/llm/client.py`
  (Anthropic/Gemini/OpenAI/OpenRouter — the providers `core/llm/adapters/` abstracts
  over). This does NOT cover observability/telemetry calls (Langfuse, Logfire) —
  those are a different concern with a different existing home: `core/hub/client.py`
  (`@langfuse_observe()`), `core/llm/middleware.py` (`CostTrackMiddleware` calls
  `langfuse.get_client()` directly), and `core/observability/` (`prompts.py`,
  `decorators.py`) all call the Langfuse SDK directly by design — `LLMClient` is a
  provider abstraction, not a generic external-API gateway, so routing telemetry
  through it would be the wrong direction, not a missing boundary. Flagged and
  clarified 2026-08-16 after CodeRabbit read the contract literally as "every"
  external API — the pre-existing `middleware.py` pattern already contradicted that
  reading before this note existed.
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
- **GET methods consolidated 2026-08-08** (survey across S01-S03 task specs, before adding
  yet another single-purpose fetch method for `s02e05_drone`): `HubClient` exposes exactly
  two public GET methods, not one-per-URL-shape.
  - `get_data(path, *, tolerate_503=False)` — `/data/{apikey}/{path}` (keyed). Default is a
    light retry (3 attempts); `tolerate_503=True` switches to the aggressive retry
    (8 attempts, longer backoff) needed for tasks with deliberately simulated outages
    (e.g. `railway`) — this replaces the old separate `get_data_503_tolerant()` method.
  - `get_public(path)` — any public GET (no apikey), `path` relative to `base_url`. This
    replaces `get_doc()` (which only covered the `/dane/doc/{path}` prefix) — the course
    uses at least four distinct public URL shapes (`dane/doc/{file}`, `dane/{file}` e.g.
    `drone.html`/`sensors.zip`, `i/{file}` e.g. `solved_electricity.png`, and root-level
    files e.g. `reactor_preview.html`), all verified to return 200. One generic method
    covers all of them instead of accumulating a near-identical method per prefix.
  - Neither method validates response *content* — only status code and retry. The hub can
    return HTTP 200 with an HTML error page instead of a real 404 for a bad binary-file URL
    (confirmed empirically). Callers that care about format MUST validate with
    `core.net.expect_binary()` / `expect_not_html()` after fetching.
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
    module docstring, not silently absent. (→ AID-62)
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

- **Tool failures reach the model with detail, not a generic string (AID-48, 2026-08-20).**
  `run_agent_loop()` formats every tool exception through `core/llm/tool_errors.py`:
  exception type, message, **HTTP status when present**, and an explicit instruction
  ("transient — retry the same call" vs "permanent — fix the arguments"). This
  **reverses** the earlier contract, which asserted the exception detail must NOT reach
  the model: without it the agent can't tell a rate limit from a bad argument and loops
  on the same call — the documented cause of the $4-10 losses in the S03E02 comments.
  - The safety half of the old rule is now carried by `tool_errors.redact()`, which is
    **mandatory, not cosmetic**: the hub takes `apikey` in the query string, so an
    unredacted network exception would write the live key straight into the model's
    conversation history. It scrubs UUIDs, `Bearer`/`Basic` headers, provider key
    prefixes (`sk-`, `ghp_`, and `AIza…` which carries **no** separator), and
    secret-named fields with either separator — `apikey=…` **and** JSON `"token": "…"`,
    since response bodies get pasted into the model's context too.
  - **Redaction applies to telemetry as well as to the model.** The handler logs the
    already-redacted result via `logfire.error(...)`, never `logfire.exception(...)`:
    the latter attaches the *active* exception with its raw message, which is exactly
    where the `apikey=` URL lives. The traceback is deliberately given up — the
    exception type plus message carries the diagnosis, and the enclosing
    `tool.<name>` span still holds the call context.
  - Error results also pass through `truncate_tool_result()` — a 5xx body can be a full
    HTML page.
- **Cost budget is Layer 2 and on by default (AID-62, 2026-08-20).** `RunBudget` carries
  `max_cost` next to `max_seconds`; `CostTrackMiddleware` feeds `record_cost()` after
  pricing a call, and `check_abort()` tests both budgets. `run.py` defaults to **$1 per
  run**; `--max-cost 0` disables it.
  - It is a **fuse, not prevention**: a call's price is only known after it is made, so
    the limit bounds the overshoot to one call.
  - `max_cost=0` means "no limit", unlike `max_seconds=0` which means "stop at once".
    That asymmetry follows the CLI flag's meaning and is deliberate.
  - Pricing is best-effort. With a budget set, `record_cost(None)` **warns loudly** —
    a silent pricing failure would leave a run looking protected while it is not.
- **`/api/*` is throttled before sending; 429 is not retried in a loop (AID-46,
  2026-08-20).** One `OutgoingThrottle` per `HubClient` (the hub limits per API key, not
  per endpoint) enforces a minimum interval **before** each request. A 429 buys one long
  cooldown and at most one retry; a second 429 propagates to the caller, which reads as
  an actionable "transient" via `tool_errors`. 429 is deliberately **out** of the tenacity
  predicate (`_is_retryable_transport_error`) because the S03E02 notes suspect each 429
  extends the block window, making a retry loop actively harmful. `/verify` keeps its own
  server-directed path (`retry_after` in the body).
- **`ToolCall.id` must be unique within one response (AID-18, 2026-08-20).** The Gemini
  adapter falls back to `f"{name}-{index}"` when the SDK omits an id — the previous
  fallback to the bare tool name collided whenever a model called the same tool twice in
  one response, breaking a contract Anthropic and OpenAI adapters already hold.
- **`run_agent_loop(tools=...)` accepts a callable (AID-50, 2026-08-20).** Pass
  `list[Tool]` as before, or a zero-arg callable returning the current list, re-evaluated
  at the start of every iteration. This is what makes runtime tool discovery possible
  (`s03e05` has no static list — only `/api/toolsearch`, returning 3 matches per query).
  The task owns the registry; `core` deliberately does not, so AID-49 (tool registry /
  schema-from-signature) stays an independent decision.

## Work Guidance
- Follow the Adapter pattern for new LLM providers.
- Maintain consistent interface usage across adapters.
- **Observability contract lives in `strategy/observability.md`**, not here — role split
  between Logfire (traces/spans) and Langfuse (prompt registry + generations).
  **Fixed 2026-08-16** (`feat/core-observability-langfuse`, before `s03e01`): `structured()`
  and `run_agent_loop()` now route through `self._chain` like `chat()` — `complete_structured()`
  changed ABC signature from `-> T` to `-> LLMResponse` (parsed model lives in the new
  `LLMResponse.parsed` field, `types.py`) so `CostTrackMiddleware` sees tokens/cost for
  every call shape uniformly. `ProviderCallMiddleware.handle()` dispatches on
  `kwargs["schema"]`/`kwargs["tools"]` — both popped before reaching the provider.
  All four call sites (`chat`/`structured`/`run_agent_loop`, plus every tool call inside
  the agent loop) now also emit a Langfuse observation; `LLMClient` methods accept an
  optional `prompt_name=` linking the generation to a version registered via
  `core.observability.prompts.sync_prompt()`. `propagate_attrs()` (existed since before,
  never called) is now wired into `BaseTask.run()` — every task run gets a `session_id`.
- **Cost tracking was silently broken since before this fix, found by the first real
  run through the newly-wired path (`s03e01`, 2026-08-16):** `CostTrackMiddleware`
  called `genai_prices.calculate(model=, input_tokens=, output_tokens=)` — an API from
  an older version of the package. The installed version only has `calc_price(Usage(...),
  model_ref)` returning `PriceCalculation.total_price` (`Decimal`). The `except Exception`
  around it (best-effort by design) swallowed the `AttributeError` silently for every
  call — nobody noticed because `chat()` (the only call type reaching this code before
  the middleware fix above) is barely used in practice. Fixed in the same commit;
  covered by `tests/core/llm/test_middleware.py::test_cost_is_actually_calculated_for_a_known_model`,
  deliberately without mocking `genai_prices` — that's exactly what a mock would have hidden.
- Anthropic-only native tools (`core/llm/native_tool_*.py`) are standalone functions,
  not `AnthropicAdapter` methods — each builds its own `anthropic.Anthropic(api_key=...)`
  client rather than reaching into adapter internals. This keeps every native-tool module
  a net-new file with zero shared-code edits, so independent tool branches (see root
  AGENTS.md batch implementation workflow) never conflict regardless of merge order.

## Verification
- Run tests in `tests/core/` before committing.

## Child DOX Index
- None.
