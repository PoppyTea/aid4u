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
- **Model identifiers are validated at construction, against the adapter's roster.**
  `ANTHROPIC_MODELS` / `OPENAI_MODELS` / `GEMINI_MODELS` in `core/llm/adapters/` are the
  single source of truth for which models this project may use; `create_provider()`
  rejects anything else with a `ValueError` that lists the allowed ids. Do not restate
  model ids in prose anywhere — a second list drifts silently, and `strategy/` is
  explicitly barred from holding this kind of state.
  - The rosters are an **anti-hallucination barrier**, not a cheatsheet. Prefix routing
    alone does not catch a dead id: `gemini-1.5-pro` passes as a valid `gemini-*` and the
    failure surfaces seconds later, wrapped by the SDK. This is not hypothetical — the
    project default was once the nonexistent `gemini-3.1-flash`, found only by
    `client.models.list()` on 2026-08-16.
  - `GEMINI_MODELS` is nested (`standard`/`premium` → capability tier) because Gemini is
    the only provider crossing a **billing** tier with a **capability** tier. Validation
    flattens the roster: the billing tier picks the *key*, not which models exist, so
    splitting the allowlist per tier would reject valid ids for no gain.
  - Escape hatch: `create_provider(..., allow_unknown_model=True)` / `--allow-unknown-model`.
    Using it means the roster needs updating — it is a signal, not a workaround.
  - Freshness is maintained by `deprecation-watch` weekly — and it must probe with a
    **real call per key**, not `models.list()` alone. Measured 2026-08-23: `models.list()`
    happily returned `gemini-2.5-flash-lite` and `gemini-2.5-pro`, both of which answer
    404 on either key, and `gemini-2.5-flash` answers 404 on the premium key while working
    on the standard one ("no longer available to new users" — the free project is
    grandfathered). The global catalogue does not answer "can *this* key call it".
    OpenRouter has no roster (adapter unimplemented, AID-61).
  - **`GeminiAdapter._thinking_config()` picks the thinking contract by model family** —
    2.5.x takes `thinking_budget`, 3.x takes `thinking_level`, and mixing both in one
    request is a 400. `gemini-3.1-pro-preview` additionally rejects a zero budget outright
    ("This model only works in thinking mode"), so hardcoding `thinking_budget=0` breaks
    `complete_structured()` for the premium `powerful` tier.
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
- **`temperature` is provider-asymmetric, by force of the Anthropic API.** It stays a real
  parameter on the ABC and on the Gemini/OpenAI adapters (default `0.0`, `None` means "leave
  the provider default"). The `AnthropicAdapter` accepts it for ABC conformance and
  **deliberately does not forward it** — anthropic 1.0.0 removed it from `messages`
  (`TypeError: Messages.create() got an unexpected keyword argument 'temperature'`,
  measured 2026-08-23). Note this asymmetry predates the migration: the adapter accepted
  the argument and silently dropped it long before, so the SDK only made it visible. If
  Anthropic ever needs it, the route is `extra_body={"temperature": ...}`. Deliberate
  cross-provider sampling control is AID-52, still open.
- **The Anthropic SDK rides on `httpx2`, the rest of the repo on `httpx` 0.x.** Both are
  installed and coexist (`anthropic` 1.0.0 imports `httpx2` 2.9.1, verified). Two
  consequences worth knowing before touching either: `core/llm/tool_errors.py` inspects
  `response` structurally rather than importing `httpx` — a deliberate choice that now
  pays off, since an `httpx`-typed `isinstance` check would silently stop matching
  Anthropic errors. And Logfire tracing is **unaffected**: `instrument_anthropic()` patches
  `client.messages.*` at the SDK level, not the transport, confirmed by a live call
  emitting a full `gen_ai.*` span on 1.0.0. Do not "fix" this by aligning the two http
  stacks — nothing is broken.
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
- `HubClient.post_api()` (used for `/api/*` endpoints, e.g. `zmail`, `shell`,
  `toolsearch`) retries 5xx/transport errors with exponential backoff (`tenacity`,
  6 attempts, 3-30s); other 4xx propagate immediately. **429 is handled separately —
  see the throttle contract under Work Guidance.** Until 2026-08-20 it was retried
  by the same tenacity predicate; that changed because `/api/*` returns no
  `retry_after` (unlike `/verify`) and the S03E02 notes suspect each 429 extends the
  block window, which makes a blind retry loop harmful rather than merely blind.
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
    Cost budget landed 2026-08-20 (`max_cost`, on by default at $1) — full contract
    under Work Guidance. A *token* budget is still absent; cost is the number that
    actually bounds the damage, so it came first.
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

- **Agent-loop guards — contracts here, rationale in `strategy/agent-loop-safety.md`.**
  That file holds the why, the trade-offs and the two bypasses found by probing; this
  list is the contract itself.
  - **Tool errors reach the model (AID-48).** `run_agent_loop()` formats every tool
    exception through `core/llm/tool_errors.py`: type, message, HTTP status when present,
    and an explicit next step (transient → retry unchanged; 401/403 → stop; other 4xx →
    fix arguments). Reverses the earlier "detail must not reach the model" rule.
  - **`redact()` is mandatory, for the model *and* for telemetry.** The handler logs via
    `logfire.error(...)`, never `logfire.exception(...)`, which would attach the raw
    exception — where the `apikey=` URL lives. Error results also pass through
    `truncate_tool_result()`.
  - **Cost budget is Layer 2, on by default at $1 (AID-62).** `RunBudget.max_cost` beside
    `max_seconds`; `CostTrackMiddleware` feeds `record_cost()`; `check_abort()` tests
    both. A fuse, not prevention. `max_cost=0` means "no limit" — unlike `max_seconds=0`.
    `record_cost(None)` warns loudly rather than counting zero.
  - **`/api/*` is throttled before sending; 429 is not retried in a loop (AID-46).** One
    `OutgoingThrottle` per `HubClient` (the hub limits per API key). A 429 buys one
    cooldown and at most one retry; a second propagates. 429 is deliberately out of
    `_is_retryable_transport_error`. `/verify` keeps its own `retry_after` path.
  - **Shell commands pass a code-enforced allowlist, never a prompt rule (AID-47).**
    `core/runtime/command_guard.py` validates before sending; `CommandRejected` becomes a
    tool error the model can act on. The default policy contains **no writing command**;
    tasks add them explicitly via `with_commands()`. Also rejected: shell metacharacters,
    control characters, `$`/`~` expansion, `..`, and globs inside path-like tokens.
    Inspects command text, not filesystem state — symlinks are invisible to it.
  - **`ToolCall.id` must be unique within one response (AID-18).** The Gemini adapter
    falls back to `f"{name}-{index}"`; the bare tool name collided on repeated calls.
  - **`run_agent_loop(tools=...)` accepts a callable (AID-50).** Re-evaluated each
    iteration, which is what makes runtime tool discovery possible. The task owns the
    registry, not `core` — AID-49 stays an independent decision.

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
