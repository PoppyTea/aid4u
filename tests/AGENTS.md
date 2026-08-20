# Tests Module

## Purpose
Project-wide test suite for verification of core components and tasks.

## Ownership
- `tests/core/`: Unit tests for `core` module.
- `tests/core/runtime/conftest.py`: shared isolation for anything touching the kill
  switch — redirects `.run/` to `tmp_path` and neutralises `os.setsid()`.

## Local Contracts
- All new features MUST have corresponding unit tests.
- **A test that calls `start_run()` MUST run under the `tests/core/runtime/` conftest.**
  Without it the test writes the repository's real `.run/` and calls `os.setsid()` on the
  pytest process, detaching it from the terminal session mid-run. Both are real effects,
  not theoretical; a test module that skipped this fixture shipped in PR #75 and was
  caught in review. The fixture lives in a conftest precisely so nobody has to remember
  to copy it.
- Tests must not touch shared repository state (`.run/`, `.cache/`, live APIs). If a test
  needs that state, it patches the module constants rather than the real paths.

## Work Guidance
- Use `pytest`.
- Keep tests isolated and fast.
- Guard tests are written against **bypass families**, not happy paths — a passing happy
  path does not distinguish a working guard from an ornament. See
  `tests/core/runtime/test_command_guard.py` and `strategy/agent-loop-safety.md`.

## Verification
- CI pipeline triggers these tests.

## Child DOX Index
- None.
