from __future__ import annotations

import pytest

from tasks.s02e01_categorize.solution import (
    CategorizeTask,
    _build_prompt,
    _validate_items,
)


def _item(code="i0001", description="Bicycle chain and derailleur mechanism"):
    return {"code": code, "description": description}


class _FakeHub:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def submit(self, task, answer):
        self.calls.append((task, answer))
        return self._responses.pop(0)


def _make_task(hub, *, dry_run=False):
    task = CategorizeTask(hub=hub, llm=None, dry_run=dry_run)
    task._task_name = "s02e01"
    task._hub_task_name = "categorize"
    return task


class TestValidateItems:
    def test_accepts_exactly_ten_valid_items(self):
        _validate_items([_item(code=f"i{n:04d}") for n in range(10)])

    def test_rejects_wrong_row_count(self):
        with pytest.raises(ValueError, match="oczekiwano 10"):
            _validate_items([_item() for _ in range(9)])

    def test_rejects_missing_description(self):
        items = [_item() for _ in range(9)] + [{"code": "i9999", "description": ""}]
        with pytest.raises(ValueError, match="code/description"):
            _validate_items(items)

    def test_rejects_non_list(self):
        with pytest.raises(ValueError):
            _validate_items(None)


class TestBuildPrompt:
    def test_includes_code_and_description(self):
        prompt = _build_prompt(_item(code="i1234", description="Stun baton"))

        assert "i1234 - Stun baton" in prompt

    def test_raises_on_missing_fields(self):
        with pytest.raises(ValueError):
            _build_prompt({"code": "i1234"})


class TestCategorizeSolve:
    def test_validation_runs_before_any_hub_call(self):
        hub = _FakeHub([])
        task = _make_task(hub)

        with pytest.raises(ValueError):
            task.solve([_item() for _ in range(9)])

        assert hub.calls == []

    def test_happy_path_resets_then_submits_nine_and_returns_tenth(self):
        items = [_item(code=f"i{n:04d}") for n in range(10)]
        hub = _FakeHub([{"code": 2}] + [{"code": 1}] * 9)
        task = _make_task(hub)

        answer = task.solve(items)

        assert len(hub.calls) == 10
        assert hub.calls[0][1] == {"prompt": "reset"}
        assert all(call[0] == "categorize" for call in hub.calls)
        assert answer == {"prompt": _build_prompt(items[-1])}

    def test_raises_on_unexpected_response_code(self):
        items = [_item(code=f"i{n:04d}") for n in range(10)]
        hub = _FakeHub([{"code": 2}, {"code": -890, "message": "wrong classification"}])
        task = _make_task(hub)

        with pytest.raises(RuntimeError, match="wrong classification"):
            task.solve(items)

    def test_dry_run_never_calls_hub_submit(self):
        items = [_item(code=f"i{n:04d}") for n in range(10)]
        hub = _FakeHub([])
        task = _make_task(hub, dry_run=True)

        answer = task.solve(items)

        assert hub.calls == []
        assert answer == {"prompt": _build_prompt(items[-1])}
