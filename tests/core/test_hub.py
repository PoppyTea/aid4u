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


class TestHubClientSubmit:
    """Testy submit() z zamockowanym HTTP."""

    def setup_method(self):
        self.hub = HubClient.__new__(HubClient)
        self.hub._apikey = "test-key"
        self.hub._base_url = "https://hub.ag3nts.org"
        self.hub._http = httpx.Client()

    @respx.mock
    def test_submit_sends_correct_payload(self):
        respx.post("https://hub.ag3nts.org/verify").mock(
            return_value=httpx.Response(200, json={"message": "{FLG:OK}"})
        )
        result = self.hub.submit("people", ["answer"])
        assert result == {"message": "{FLG:OK}"}

    @respx.mock
    def test_submit_raises_on_http_error(self):
        respx.post("https://hub.ag3nts.org/verify").mock(
            return_value=httpx.Response(500, json={"error": "server error"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            self.hub.submit("people", "bad")

    @respx.mock
    def test_submit_retries_on_503_outage(self, mocker):
        mocker.patch("time.sleep")

        route = respx.post("https://hub.ag3nts.org/verify")
        route.side_effect = [
            httpx.Response(503, json={"code": -925, "message": "Temporary server outage."}),
            httpx.Response(200, json={"message": "{FLG:OK}"}),
        ]

        result = self.hub.submit("railway", {"action": "help"})
        assert result == {"message": "{FLG:OK}"}
        assert route.call_count == 2

    @respx.mock
    def test_submit_retries_on_429_using_retry_after_from_body(self, mocker):
        mock_sleep = mocker.patch("time.sleep")

        route = respx.post("https://hub.ag3nts.org/verify")
        route.side_effect = [
            httpx.Response(429, json={"code": -985, "message": "rate limited", "retry_after": 13}),
            httpx.Response(200, json={"message": "{FLG:OK}"}),
        ]

        result = self.hub.submit("railway", {"action": "reconfigure", "route": "X-01"})
        assert result == {"message": "{FLG:OK}"}
        assert route.call_count == 2
        # Odczekuje retry_after + margines (2s), nie ślepy exponential backoff.
        mock_sleep.assert_called_once_with(15.0)

    @respx.mock
    def test_submit_exhausts_retries_on_persistent_503(self, mocker):
        mocker.patch("time.sleep")

        route = respx.post("https://hub.ag3nts.org/verify").mock(
            return_value=httpx.Response(503, json={"message": "outage"})
        )

        with pytest.raises(RuntimeError, match="wyczerpano"):
            self.hub.submit("railway", {"action": "help"})

        assert route.call_count == 20

    @respx.mock
    def test_submit_redacts_answer_in_log(self, mocker):
        # Setup mock for logfire
        mock_logfire = mocker.patch("core.hub.client.logfire.info")

        respx.post("https://hub.ag3nts.org/verify").mock(
            return_value=httpx.Response(200, json={"message": "{FLG:OK}"})
        )

        secret_answer = "SUPER_SECRET_ANSWER_DATA_123"
        self.hub.submit("secret_task", secret_answer)

        # Verify logfire.info was called to log the submission but redacted the answer
        expected_preview = "SUP****123 <str> (len: 28)"
        mock_logfire.assert_any_call("Submitting task secret_task", answer_preview=expected_preview)


class TestHubClientGetData503Tolerant:
    """Testy get_data_503_tolerant() z zamockowanym HTTP i mockowanym czasem (tenacity)."""

    def setup_method(self):
        self.hub = HubClient.__new__(HubClient)
        self.hub._apikey = "test-key"
        self.hub._base_url = "https://hub.ag3nts.org"
        self.hub._http = httpx.Client()
        self.url = f"{self.hub._base_url}/data/{self.hub._apikey}/test-file.txt"

    def teardown_method(self):
        self.hub._http.close()

    @respx.mock
    def test_success_without_retry(self):
        route = respx.get(self.url).mock(return_value=httpx.Response(200, content=b"success data"))

        result = self.hub.get_data_503_tolerant("test-file.txt")
        assert result == b"success data"
        assert route.call_count == 1

    @respx.mock
    def test_success_after_503_retries(self, mocker):
        # Pomijamy prawdziwe sleep'y w testach (przyspiesza wykonanie)
        mocker.patch("time.sleep")

        route = respx.get(self.url)
        # 2 razy 503, 3. raz sukces
        route.side_effect = [
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, content=b"recovered data"),
        ]

        result = self.hub.get_data_503_tolerant("test-file.txt")
        assert result == b"recovered data"
        assert route.call_count == 3

    @respx.mock
    def test_exhausts_retries_on_503(self, mocker):
        from tenacity import RetryError

        mocker.patch("time.sleep")

        route = respx.get(self.url).mock(return_value=httpx.Response(503))

        with pytest.raises(RetryError):
            self.hub.get_data_503_tolerant("test-file.txt")

        # Zgodnie z @retry(stop=stop_after_attempt(8))
        assert route.call_count == 8


class TestHubClientGetData:
    """Testy get_data() z zamockowanym HTTP i mockowanym czasem (tenacity)."""

    def setup_method(self):
        self.hub = HubClient.__new__(HubClient)
        self.hub._apikey = "test-key"
        self.hub._base_url = "https://hub.ag3nts.org"
        self.hub._http = httpx.Client()
        self.url = f"{self.hub._base_url}/data/{self.hub._apikey}/test-file.txt"

    def teardown_method(self):
        self.hub._http.close()

    @respx.mock
    def test_get_data_success_without_retry(self):
        route = respx.get(self.url).mock(return_value=httpx.Response(200, content=b"success data"))

        result = self.hub.get_data("test-file.txt")
        assert result == b"success data"
        assert route.call_count == 1

    @respx.mock
    def test_get_data_success_after_retries(self, mocker):
        # Pomijamy prawdziwe sleep'y w testach (przyspiesza wykonanie)
        mocker.patch("time.sleep")

        route = respx.get(self.url)
        # 2 razy błąd (np. 500), 3. raz sukces
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, content=b"recovered data"),
        ]

        result = self.hub.get_data("test-file.txt")
        assert result == b"recovered data"
        assert route.call_count == 3

    @respx.mock
    def test_get_data_exhausts_retries(self, mocker):
        from tenacity import RetryError

        mocker.patch("time.sleep")

        route = respx.get(self.url).mock(return_value=httpx.Response(500))

        with pytest.raises(RetryError):
            self.hub.get_data("test-file.txt")

        # Zgodnie z @retry(stop=stop_after_attempt(3))
        assert route.call_count == 3


class TestHubClientGetDoc:
    """Testy get_doc() — retry na 5xx/timeout, ale NIE na 4xx (path trwale błędny)."""

    def setup_method(self):
        self.hub = HubClient.__new__(HubClient)
        self.hub._apikey = "test-key"
        self.hub._base_url = "https://hub.ag3nts.org"
        self.hub._http = httpx.Client()
        self.url = f"{self.hub._base_url}/dane/doc/test-file.md"

    def teardown_method(self):
        self.hub._http.close()

    @respx.mock
    def test_get_doc_success_without_retry(self):
        route = respx.get(self.url).mock(return_value=httpx.Response(200, content=b"doc content"))

        result = self.hub.get_doc("test-file.md")
        assert result == b"doc content"
        assert route.call_count == 1

    @respx.mock
    def test_get_doc_success_after_5xx_retries(self, mocker):
        mocker.patch("time.sleep")

        route = respx.get(self.url)
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(503),
            httpx.Response(200, content=b"recovered doc"),
        ]

        result = self.hub.get_doc("test-file.md")
        assert result == b"recovered doc"
        assert route.call_count == 3

    @respx.mock
    def test_get_doc_404_not_retried(self):
        route = respx.get(self.url).mock(return_value=httpx.Response(404))

        with pytest.raises(httpx.HTTPStatusError):
            self.hub.get_doc("test-file.md")

        # Kluczowa różnica względem get_data(): 4xx nie jest powtarzane.
        assert route.call_count == 1


class TestHubClientTeardown:
    """Testy dla metody __del__ HubClient."""

    def test_del_closes_http_client(self, mocker):
        hub = HubClient.__new__(HubClient)
        mock_http = mocker.MagicMock(spec=httpx.Client)
        hub._http = mock_http

        hub.__del__()
        mock_http.close.assert_called_once()

    def test_del_logs_warning_on_http_error(self, mocker):
        hub = HubClient.__new__(HubClient)
        mock_http = mocker.MagicMock(spec=httpx.Client)
        error = httpx.HTTPError("Mocked socket close error")
        mock_http.close.side_effect = error
        hub._http = mock_http

        mock_logfire = mocker.patch("core.hub.client.logfire.warning")

        hub.__del__()
        mock_http.close.assert_called_once()
        mock_logfire.assert_called_once_with("Failed to close HubClient HTTP session", error=error)

    def test_del_swallows_other_exceptions_silently(self, mocker):
        hub = HubClient.__new__(HubClient)
        mock_http = mocker.MagicMock(spec=httpx.Client)
        mock_http.close.side_effect = RuntimeError("Generic unexpected error")
        hub._http = mock_http

        mock_logfire = mocker.patch("core.hub.client.logfire.warning")

        # Ten wywołanie nie powinno rzucić wyjątku
        hub.__del__()
        mock_http.close.assert_called_once()
        mock_logfire.assert_not_called()

    def test_del_handles_missing_or_none_http_attribute(self):
        hub = HubClient.__new__(HubClient)
        # self._http nie jest ustawione wcale
        hub.__del__()

        hub2 = HubClient.__new__(HubClient)
        hub2._http = None
        hub2.__del__()


class TestHubClientPostApi:
    """Testy post_api() z zamockowanym HTTP."""

    def setup_method(self):
        self.hub = HubClient.__new__(HubClient)
        self.hub._apikey = "test-key"
        self.hub._base_url = "https://hub.ag3nts.org"
        self.hub._http = httpx.Client()

    def teardown_method(self):
        self.hub._http.close()

    @respx.mock
    def test_post_api_success(self):
        # Setup mock route
        url = f"{self.hub._base_url}/api/test-endpoint"
        # We expect a payload with "foo": "bar" and "apikey": "test-key"
        route = respx.post(url).mock(
            return_value=httpx.Response(200, json={"status": "ok", "result": 123})
        )

        result = self.hub.post_api("/api/test-endpoint", {"foo": "bar"})

        assert result == {"status": "ok", "result": 123}
        assert route.call_count == 1

        # Verify the requested JSON body contained key and parameter
        last_request = route.calls.last.request
        import json
        request_body = json.loads(last_request.content)
        assert request_body == {"foo": "bar", "apikey": "test-key"}

    @respx.mock
    def test_post_api_raises_on_http_error(self):
        url = f"{self.hub._base_url}/api/test-endpoint"
        respx.post(url).mock(
            return_value=httpx.Response(400, json={"error": "bad request"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            self.hub.post_api("/api/test-endpoint", {"foo": "bar"})
