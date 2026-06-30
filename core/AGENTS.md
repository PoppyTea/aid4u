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
- Any new task MUST inherit from `core/tasks/base.py` and be decorated with `@task`.

## Work Guidance
- Follow the Adapter pattern for new LLM providers.
- Maintain consistent interface usage across adapters.

## Verification
- Run tests in `tests/core/` before committing.

## Child DOX Index
- None.
