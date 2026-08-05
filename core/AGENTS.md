# Core Module

## Purpose
Contains the architectural heart of the system: LLM clients, task management bases, observability instrumentation, and hub connectivity.

## Ownership
- `core/llm/`: LLM integration and adapter logic.
- `core/hub/`: Data acquisition and caching.
- `core/tasks/`: Base classes for task registration.
- `core/observability/`: Instrumentation and tracing decorators.

## Local Contracts
- All external API interactions MUST go through `core/llm/client.py`.
  - **Exception:** `core/llm/native_tool_*.py` (Anthropic native tools — web_search,
    code_execution, bash, text_editor) call `anthropic.Anthropic` directly instead of
    going through `LLMClient`. These aren't portable across providers, so they're a
    deliberate, narrow exception — not a precedent for other bypasses.
- Any new task MUST inherit from `core/tasks/base.py` and be decorated with `@task`.
- `HubClient.submit()` retries transparently on `/verify` 503 (simulated outage) and
  429 (rate limit) — for 429 it waits on the `retry_after` field from the JSON
  response body (the hub does not set a standard `Retry-After` header). It raises
  `RuntimeError` after exhausting attempts. Callers can invoke `submit()` more than
  once per task run for multi-step hub protocols (e.g. `s01e05_railway`), not just
  for the final answer — each call gets the same resilience.
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
