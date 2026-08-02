from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.tasks import TASK_REGISTRY
from tasks.s01e03_proxy.solution import ProxyTask, register_with_hub


def test_task_registered_in_registry():
    assert TASK_REGISTRY["s01e03"] is ProxyTask


def test_task_uses_proxy_as_hub_name_not_local_slug():
    assert ProxyTask._hub_task_name == "proxy"


def test_solve_refuses_with_helpful_instructions_instead_of_submitting_blindly():
    task = ProxyTask.__new__(ProxyTask)  # solve() doesn't touch self — skip hub/llm __init__

    with pytest.raises(RuntimeError, match="run.py solve"):
        task.solve(None)


def test_register_with_hub_submits_proxy_task_with_url_and_session_id():
    hub = MagicMock()
    hub.submit.return_value = {"ok": True}

    result = register_with_hub(hub, "https://abc123.ngrok-free.app", "test-session-1")

    hub.submit.assert_called_once_with(
        "proxy", {"url": "https://abc123.ngrok-free.app", "sessionID": "test-session-1"}
    )
    assert result == {"ok": True}
