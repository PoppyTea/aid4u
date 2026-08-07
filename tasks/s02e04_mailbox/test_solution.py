from __future__ import annotations

import httpx
import pytest

from tasks.s02e04_mailbox import solution


class _FakeHub:
    def __init__(self, *, post_api_response=None, post_api_error=None, submit_response=None):
        self.post_api_calls: list[tuple[str, dict]] = []
        self.submit_calls: list[tuple[str, dict]] = []
        self._post_api_response = post_api_response or {"ok": True}
        self._post_api_error = post_api_error
        self._submit_response = submit_response or {"ok": True}

    def post_api(self, path, payload):
        self.post_api_calls.append((path, payload))
        if self._post_api_error is not None:
            raise self._post_api_error
        return self._post_api_response

    def submit(self, task, answer):
        self.submit_calls.append((task, answer))
        return self._submit_response

    @staticmethod
    def get_flag(response):
        return response.get("flag")


VALID_CODE = "SEC-c1e598764329cc9c377ef1d029be8ceb"


class TestZmailAction:
    def test_dispatches_to_post_api_with_action_and_params(self, monkeypatch):
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub(post_api_response={"ok": True, "items": []})
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        executor("zmail_action", {"action": "search", "params": {"query": "from:proton.me"}})

        assert hub.post_api_calls == [
            (solution.ZMAIL_API_PATH, {"action": "search", "query": "from:proton.me"})
        ]

    def test_surfaces_4xx_as_tool_result_instead_of_raising(self, monkeypatch):
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        request = httpx.Request("POST", "https://hub.ag3nts.org/api/zmail")
        response = httpx.Response(400, json={"code": -1, "message": "Unknown action"}, request=request)
        error = httpx.HTTPStatusError("400", request=request, response=response)
        hub = _FakeHub(post_api_error=error)
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        result = executor("zmail_action", {"action": "bogus"})

        assert "Unknown action" in result
        assert "400" in result

    def test_5xx_still_propagates(self, monkeypatch):
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        request = httpx.Request("POST", "https://hub.ag3nts.org/api/zmail")
        response = httpx.Response(500, json={"message": "oops"}, request=request)
        error = httpx.HTTPStatusError("500", request=request, response=response)
        hub = _FakeHub(post_api_error=error)
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        with pytest.raises(httpx.HTTPStatusError):
            executor("zmail_action", {"action": "help"})


class TestSubmitAnswer:
    def test_rejects_bad_confirmation_code_locally_without_calling_hub(self, monkeypatch):
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub()
        executor, state = solution.build_tool_executor(hub, dry_run=False)

        result = executor(
            "submit_answer",
            {"password": "x", "date": "2026-03-23", "confirmation_code": "SEC-tooshort"},
        )

        assert hub.submit_calls == []
        assert "Lokalna walidacja" in result
        assert state["last_submission"] == {
            "password": "x",
            "date": "2026-03-23",
            "confirmation_code": "SEC-tooshort",
        }

    def test_valid_answer_calls_hub_submit_and_captures_flag(self, monkeypatch):
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub(submit_response={"ok": True, "flag": "{FLG:TRAITOR}"})
        executor, state = solution.build_tool_executor(hub, dry_run=False)

        executor(
            "submit_answer",
            {"password": "RABARBAR25", "date": "2026-03-23", "confirmation_code": VALID_CODE},
        )

        assert hub.submit_calls == [
            (
                solution.HUB_TASK_NAME,
                {"password": "RABARBAR25", "date": "2026-03-23", "confirmation_code": VALID_CODE},
            )
        ]
        assert state["flag"] == "{FLG:TRAITOR}"

    def test_dry_run_does_not_call_hub_submit(self, monkeypatch):
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub()
        executor, state = solution.build_tool_executor(hub, dry_run=True)

        result = executor(
            "submit_answer",
            {"password": "x", "date": "2026-03-23", "confirmation_code": VALID_CODE},
        )

        assert hub.submit_calls == []
        assert '"dry_run": true' in result
        assert state["last_submission"]["password"] == "x"


class TestWaitSeconds:
    def test_clamps_to_min_and_max(self, monkeypatch):
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub()
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        too_low = executor("wait_seconds", {"seconds": 0})
        too_high = executor("wait_seconds", {"seconds": 10_000})

        assert f'"waited_s": {solution._WAIT_MIN_S}' in too_low
        assert f'"waited_s": {solution._WAIT_MAX_S}' in too_high

    def test_refuses_once_budget_is_exhausted(self, monkeypatch):
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        monkeypatch.setattr(solution, "_WAIT_BUDGET_TOTAL_S", 5.0)
        hub = _FakeHub()
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        first = executor("wait_seconds", {"seconds": 5})
        second = executor("wait_seconds", {"seconds": 5})

        assert '"ok": true' in first
        assert "wyczerpany" in second
