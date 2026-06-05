"""Testy jednostkowe HubClient — bez sieci (respx do mockowania HTTP)."""
from __future__ import annotations

import pytest
import respx
import httpx

from core.hub.client import HubClient, _FLAG_PATTERN


class TestFlagExtraction:
    """Testy ekstrakcji flagi z odpowiedzi hubu."""

    def setup_method(self):
        # HubClient nie wymaga sieci dla get_flag()
        self.hub = HubClient.__new__(HubClient)
        self.hub._apikey = "test-key"
        self.hub._base_url = "https://hub.ag3nts.org"

    def test_extracts_flag_from_message_field(self):
        response = {"message": "Gratulacje! {FLG:TESTFLAG}"}
        assert self.hub.get_flag(response) == "{FLG:TESTFLAG}"

    def test_extracts_flag_from_msg_field(self):
        response = {"msg": "{FLG:ANOTHER}"}
        assert self.hub.get_flag(response) == "{FLG:ANOTHER}"

    def test_returns_none_when_no_flag(self):
        response = {"message": "Błąd: nieprawidłowa odpowiedź"}
        assert self.hub.get_flag(response) is None

    def test_extracts_from_nested_string(self):
        response = {"message": "Odpowiedź OK. Flaga: {FLG:DEEP} — zachowaj ją."}
        assert self.hub.get_flag(response) == "{FLG:DEEP}"

    def test_flag_pattern_matches_alphanumeric(self):
        assert _FLAG_PATTERN.search("{FLG:PIZZA_2025}") is not None
        assert _FLAG_PATTERN.search("{FLG:}") is None  # pusta flaga
        assert _FLAG_PATTERN.search("FLG:NOOUTER") is None  # brak nawiasów


@respx.mock
class TestHubClientSubmit:
    """Testy submit() z zamockowanym HTTP."""

    def setup_method(self):
        self.hub = HubClient.__new__(HubClient)
        self.hub._apikey = "test-key"
        self.hub._base_url = "https://hub.ag3nts.org"
        self.hub._http = httpx.Client()

    def test_submit_sends_correct_payload(self):
        respx.post("https://hub.ag3nts.org/verify").mock(
            return_value=httpx.Response(200, json={"message": "{FLG:OK}"})
        )
        result = self.hub.submit("people", ["answer"])
        assert result == {"message": "{FLG:OK}"}

    def test_submit_raises_on_http_error(self):
        respx.post("https://hub.ag3nts.org/verify").mock(
            return_value=httpx.Response(500, json={"error": "server error"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            self.hub.submit("people", "bad")

    def test_submit_redacts_answer_in_log(self, mocker):
        # Setup mock for logfire
        mock_logfire = mocker.patch("core.hub.client.logfire.info")

        respx.post("https://hub.ag3nts.org/verify").mock(
            return_value=httpx.Response(200, json={"message": "{FLG:OK}"})
        )

        secret_answer = "SUPER_SECRET_ANSWER_DATA_123"
        self.hub.submit("secret_task", secret_answer)

        # Verify logfire.info was called to log the submission but redacted the answer
        expected_preview = "SUP****123<str> (len: 28)"
        mock_logfire.assert_any_call(
            "Submitting task secret_task",
            answer_preview=expected_preview
        )
