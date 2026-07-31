from __future__ import annotations

import pytest

from core.tasks import TASK_REGISTRY
from tasks.s01e03_proxy.solution import ProxyTask


def test_task_registered_in_registry():
    assert TASK_REGISTRY["s01e03"] is ProxyTask


def test_solve_refuses_with_helpful_instructions_instead_of_submitting_blindly():
    task = ProxyTask.__new__(ProxyTask)  # solve() doesn't touch self — skip hub/llm __init__

    with pytest.raises(RuntimeError, match="run.py solve"):
        task.solve(None)
