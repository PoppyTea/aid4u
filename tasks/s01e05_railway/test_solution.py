from __future__ import annotations

import pytest

from tasks.s01e05_railway.solution import ROUTE, RailwayTask


class _FakeHub:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def submit(self, task, answer):
        self.calls.append((task, answer))
        return self._responses.pop(0)


def _make_task(hub, *, dry_run=False):
    task = RailwayTask(hub=hub, llm=None, dry_run=dry_run)
    task._task_name = "s01e05"
    task._hub_task_name = "railway"
    return task


class TestRailwaySolve:
    def test_calls_protocol_steps_in_order_and_returns_save_action(self):
        hub = _FakeHub([{"ok": True}, {"ok": True}, {"ok": True}])
        task = _make_task(hub)

        answer = task.solve(None)

        assert [call[1]["action"] for call in hub.calls] == ["help", "reconfigure", "setstatus"]
        assert hub.calls[1][1] == {"action": "reconfigure", "route": ROUTE}
        assert hub.calls[2][1] == {"action": "setstatus", "route": ROUTE, "value": "RTOPEN"}
        assert all(call[0] == "railway" for call in hub.calls)
        assert answer == {"action": "save", "route": ROUTE}

    def test_raises_on_ok_false_response(self):
        hub = _FakeHub([{"ok": False, "message": "boom"}])
        task = _make_task(hub)

        with pytest.raises(RuntimeError, match="boom"):
            task.solve(None)

    def test_dry_run_never_calls_hub_submit(self):
        hub = _FakeHub([])
        task = _make_task(hub, dry_run=True)

        answer = task.solve(None)

        assert hub.calls == []
        assert answer == {"action": "save", "route": ROUTE}
