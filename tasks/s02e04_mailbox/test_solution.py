"""Testy dispatchu narzędzi s02e04 (mock HubClient, bez sieci)."""

from __future__ import annotations

import httpx
import pytest

from tasks.s02e04_mailbox import solution


class _FakeHub:
    """Minimalny podstaw HubClient nagrywający wywołania post_api/submit."""

    def __init__(self, *, post_api_response=None, post_api_error=None, submit_response=None):
        """Konfiguruje zwracane/rzucane odpowiedzi i puste listy nagranych wywołań."""
        self.post_api_calls: list[tuple[str, dict]] = []
        self.submit_calls: list[tuple[str, dict]] = []
        self._post_api_response = post_api_response or {"ok": True}
        self._post_api_error = post_api_error
        self._submit_response = submit_response or {"ok": True}

    def post_api(self, path, payload):
        """Nagrywa wywołanie i zwraca skonfigurowaną odpowiedź albo rzuca skonfigurowany błąd."""
        self.post_api_calls.append((path, payload))
        if self._post_api_error is not None:
            raise self._post_api_error
        return self._post_api_response

    def submit(self, task, answer):
        """Nagrywa wywołanie /verify i zwraca skonfigurowaną odpowiedź."""
        self.submit_calls.append((task, answer))
        return self._submit_response

    @staticmethod
    def get_flag(response):
        """Odpowiednik HubClient.get_flag — czyta pole 'flag' wprost, bez regexa."""
        return response.get("flag")


VALID_CODE = "SEC-c1e598764329cc9c377ef1d029be8ceb"


class TestZmailAction:
    """Zachowanie narzędzia zmail_action zwracanego przez build_tool_executor."""

    def test_dispatches_to_post_api_with_action_and_params(self, monkeypatch):
        """zmail_action spłaszcza action+params do jednego payloadu dla post_api."""
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub(post_api_response={"ok": True, "items": []})
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        executor("zmail_action", {"action": "search", "params": {"query": "from:proton.me"}})

        assert hub.post_api_calls == [
            (solution.ZMAIL_API_PATH, {"action": "search", "query": "from:proton.me"})
        ]

    def test_explicit_action_wins_over_params_action_key(self, monkeypatch):
        """params={'action': 'evil'} nie może po cichu podmienić wywołanej akcji."""
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub()
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        executor("zmail_action", {"action": "help", "params": {"action": "evil", "page": 1}})

        assert hub.post_api_calls == [(solution.ZMAIL_API_PATH, {"action": "help", "page": 1})]

    def test_non_dict_params_returns_error_instead_of_raising(self, monkeypatch):
        """params malformowany przez model (np. lista) daje strukturalny błąd, nie wyjątek."""
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub()
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        result = executor("zmail_action", {"action": "help", "params": ["not", "a", "dict"]})

        assert hub.post_api_calls == []
        assert "params musi być obiektem" in result

    def test_surfaces_4xx_as_tool_result_instead_of_raising(self, monkeypatch):
        """400 z zmail wraca jako JSON-feedback dla agenta, nie jako wyjątek."""
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
        """500 nie jest połykany lokalnie — HubClient.post_api() już go wyczerpał retry-ami."""
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        request = httpx.Request("POST", "https://hub.ag3nts.org/api/zmail")
        response = httpx.Response(500, json={"message": "oops"}, request=request)
        error = httpx.HTTPStatusError("500", request=request, response=response)
        hub = _FakeHub(post_api_error=error)
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        with pytest.raises(httpx.HTTPStatusError):
            executor("zmail_action", {"action": "help"})


class TestSubmitAnswer:
    """Zachowanie narzędzia submit_answer — walidacja lokalna, dry-run, flaga."""

    def test_rejects_bad_confirmation_code_locally_without_calling_hub(self, monkeypatch):
        """Zły format confirmation_code nie trafia w ogóle do hub.submit()."""
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub()
        executor, state = solution.build_tool_executor(hub, dry_run=False)

        result = executor(
            "submit_answer",
            {"password": "x", "date": "2026-03-23", "confirmation_code": "SEC-tooshort"},
        )

        assert hub.submit_calls == []
        assert "Lokalna walidacja" in result
        assert state["last_submission"] is None

    def test_rejects_code_with_non_alphanumeric_characters(self, monkeypatch):
        """32 znaki po prefiksie muszą być ASCII alfanumeryczne, nie tylko odpowiedniej długości."""
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub()
        executor, state = solution.build_tool_executor(hub, dry_run=False)
        bad_code = "SEC-" + ("!" * 32)

        result = executor(
            "submit_answer",
            {"password": "x", "date": "2026-03-23", "confirmation_code": bad_code},
        )

        assert hub.submit_calls == []
        assert "Lokalna walidacja" in result
        assert state["last_submission"] is None

    def test_valid_answer_calls_hub_submit_and_captures_flag(self, monkeypatch):
        """Poprawny format trafia do hub.submit(), a zwrócona flaga ląduje w stanie."""
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
        """W trybie dry-run submit_answer nigdy nie dotyka sieci (/verify)."""
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
    """Zachowanie narzędzia wait_seconds — clamp per-call i budżet skumulowany."""

    def test_clamps_to_min_and_max(self, monkeypatch):
        """Wartości spoza [_WAIT_MIN_S, _WAIT_MAX_S] są przycinane, nie odrzucane."""
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        hub = _FakeHub()
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        too_low = executor("wait_seconds", {"seconds": 0})
        too_high = executor("wait_seconds", {"seconds": 10_000})

        assert f'"waited_s": {solution._WAIT_MIN_S}' in too_low
        assert f'"waited_s": {solution._WAIT_MAX_S}' in too_high

    def test_refuses_once_budget_is_exhausted(self, monkeypatch):
        """Po wyczerpaniu skumulowanego budżetu kolejne wait_seconds odmawiają czekania."""
        monkeypatch.setattr(solution.time, "sleep", lambda *_: None)
        monkeypatch.setattr(solution, "_WAIT_BUDGET_TOTAL_S", 5.0)
        hub = _FakeHub()
        executor, _ = solution.build_tool_executor(hub, dry_run=False)

        first = executor("wait_seconds", {"seconds": 5})
        second = executor("wait_seconds", {"seconds": 5})

        assert '"ok": true' in first
        assert "wyczerpany" in second


class TestSubmitDedup:
    """MailboxTask._submit() musi pominąć redundantny drugi /verify po sukcesie w pętli."""

    def test_skips_hub_submit_when_flag_already_captured(self):
        """Gdy submit_answer już złapał flagę, BaseTask.run()'s finalny _submit nie dubluje wywołania."""
        hub = _FakeHub(submit_response={"ok": True, "flag": "{FLG:SHOULD_NOT_BE_CALLED}"})
        mailbox_task = solution.MailboxTask(hub=hub, llm=None, dry_run=False)
        mailbox_task._captured_flag = "{FLG:TRAITOR}"

        result = mailbox_task._submit("mailbox", {"password": "x", "date": "y", "confirmation_code": "z"})

        assert result == "{FLG:TRAITOR}"
        assert hub.submit_calls == []

    def test_calls_hub_submit_when_no_flag_was_captured(self):
        """Bez wcześniej złapanej flagi _submit działa jak domyślny BaseTask._submit."""
        hub = _FakeHub(submit_response={"ok": True, "flag": "{FLG:TRAITOR}"})
        mailbox_task = solution.MailboxTask(hub=hub, llm=None, dry_run=False)

        result = mailbox_task._submit("mailbox", {"password": "x", "date": "y", "confirmation_code": "z"})

        assert result == "{FLG:TRAITOR}"
        assert hub.submit_calls == [("mailbox", {"password": "x", "date": "y", "confirmation_code": "z"})]
