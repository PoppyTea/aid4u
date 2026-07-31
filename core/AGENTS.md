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
