"""Fixtures shared across the whole test suite (testpaths: tasks/ + tests/)."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_keyring_circuit_breaker():
    """core.secrets._keyring_unavailable_until is module-global state — a real
    keyring timeout during ANY test's collection (e.g. tasks/s01e03_proxy/
    test_server.py imports server.py, which calls setup_observability() at
    module level, which reads cfg.logfire_token for real) trips it for
    _KEYRING_BACKOFF_SECONDS (minutes), silently poisoning every later test in
    the same run that expects keyring.get_password() to actually be invoked
    — mocked or not. Reset around every test so no test's outcome depends on
    ambient keyring health or collection/execution order.
    """
    import core.secrets as secrets_module

    secrets_module._keyring_unavailable_until = None
    yield
    secrets_module._keyring_unavailable_until = None
