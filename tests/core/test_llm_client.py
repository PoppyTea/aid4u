"""Testy LLMClient z zamockowanym providerem."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

from core.llm.client import LLMClient
from core.llm.types import LLMMessage, LLMResponse, Tool, ToolCall
from core.runtime import AbortRun


def make_response(content: str, tool_calls=None) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="claude-test",
        input_tokens=10,
        output_tokens=5,
        tool_calls=tool_calls or [],
    )


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.model_name = "claude-test"
    return provider


@pytest.fixture
def llm(mock_provider):
    # Bypass middleware przy testach — testujemy logikę klienta, nie pipeline
    client = LLMClient.__new__(LLMClient)
    client._provider = mock_provider
    # Prosta chain bez rate limit / cost tracking dla szybkich testów
    from core.llm.middleware import ProviderCallMiddleware

    client._chain = ProviderCallMiddleware(mock_provider)
    return client


class TestLLMClientChat:
    def test_returns_string(self, llm, mock_provider):
        mock_provider.complete.return_value = make_response("Odpowiedź")
        result = llm.chat([LLMMessage.user("Pytanie")])
        assert result == "Odpowiedź"

    def test_passes_system_prompt(self, llm, mock_provider):
        mock_provider.complete.return_value = make_response("ok")
        llm.chat([LLMMessage.user("test")], system="Jesteś pomocnikiem")
        call_kwargs = mock_provider.complete.call_args.kwargs
        assert call_kwargs["system"] == "Jesteś pomocnikiem"


class TestLLMClientStructured:
    def test_parses_pydantic_model(self, llm, mock_provider):
        class MySchema(BaseModel):
            name: str
            age: int

        parsed = MySchema(name="Jan", age=30)
        mock_provider.complete_structured.return_value = LLMResponse(
            content=parsed.model_dump_json(),
            model="claude-test",
            input_tokens=10,
            output_tokens=5,
            parsed=parsed,
        )
        result = llm.structured([LLMMessage.user("test")], MySchema)
        assert isinstance(result, MySchema)
        assert result.name == "Jan"


class TestAgentLoop:
    def test_stops_when_no_tool_calls(self, llm, mock_provider):
        mock_provider.complete_with_tools.return_value = make_response("Gotowe!")
        result = llm.run_agent_loop(
            [LLMMessage.user("Zadanie")],
            tools=[Tool("search", "Szuka informacji", {})],
            tool_executor=lambda name, args: "wynik",
        )
        assert result == "Gotowe!"
        assert mock_provider.complete_with_tools.call_count == 1

    def test_executes_tool_and_continues(self, llm, mock_provider):
        tool_call = ToolCall(id="c1", name="search", arguments={"query": "test"})
        # Pierwsza iteracja: zwróć tool call
        # Druga iteracja: zakończ bez tool calls
        mock_provider.complete_with_tools.side_effect = [
            make_response("Szukam...", tool_calls=[tool_call]),
            make_response("Znalazłem!"),
        ]
        executor = MagicMock(return_value="wynik wyszukiwania")
        result = llm.run_agent_loop(
            [LLMMessage.user("Szukaj czegoś")],
            tools=[Tool("search", "Szuka", {})],
            tool_executor=executor,
        )
        assert result == "Znalazłem!"
        executor.assert_called_once_with("search", {"query": "test"})

    def test_respects_max_iterations(self, llm, mock_provider):
        tool_call = ToolCall(id="c1", name="loop", arguments={})
        # Zawsze zwracaj tool calls → pętla nieskończona bez limitu
        mock_provider.complete_with_tools.return_value = make_response(
            "...", tool_calls=[tool_call]
        )
        _ = llm.run_agent_loop(
            [LLMMessage.user("test")],
            tools=[Tool("loop", "Zapętla", {})],
            tool_executor=lambda n, a: "ok",
            max_iterations=3,
        )
        assert mock_provider.complete_with_tools.call_count == 3

    @patch("logfire.error")
    def test_tool_executor_error_doesnt_crash_loop(
        self, mock_logfire_error, llm, mock_provider
    ):
        tool_call = ToolCall(id="c1", name="broken", arguments={})
        mock_provider.complete_with_tools.side_effect = [
            make_response("", tool_calls=[tool_call]),
            make_response("Mimo błędu kontynuuję"),
        ]

        def bad_executor(name, args):
            raise RuntimeError("Narzędzie się posypało")

        result = llm.run_agent_loop(
            [LLMMessage.user("test")],
            tools=[Tool("broken", "Zepsute narzędzie", {})],
            tool_executor=bad_executor,
        )
        assert result == "Mimo błędu kontynuuję"
        # `logfire.exception()` dołączałoby surowy wyjątek do telemetrii; logujemy
        # zredagowany wynik, żeby redakcja obowiązywała tak samo wobec Logfire.
        mock_logfire_error.assert_called_once()
        assert mock_logfire_error.call_args.kwargs["tool_name"] == "broken"

        # KONTRAKT ODWRÓCONY 2026-08-20 (AID-48). Ten test wymagał wcześniej, żeby treść
        # wyjątku NIE docierała do modelu. To było zbyt szerokie: bez szczegółu model nie
        # odróżnia "rate limit, poczekaj" od "zły argument, popraw" i pętli się na tym
        # samym wywołaniu — źródło udokumentowanych strat $4-10 w komentarzach S03E02.
        # Treść błędu MA teraz trafiać do modelu; ochronę przed wyciekiem przejmuje
        # `redact()` (patrz tests/core/llm/test_tool_errors.py).
        history = mock_provider.complete_with_tools.call_args[0][0]
        seen = "\n".join(m.content for m in history)
        assert "Narzędzie się posypało" in seen
        assert "ERROR: Tool execution failed." not in seen

    def test_abort_run_from_tool_executor_propagates_not_swallowed(self, llm, mock_provider):
        """Kontrakt z core/AGENTS.md: AbortRun to sygnał kill switcha, nie awaria narzędzia —
        MUSI przelecieć przez run_agent_loop(), nie zostać połknięte jak generyczny wyjątek
        (patrz test_tool_executor_error_doesnt_crash_loop powyżej — to jest jego przeciwieństwo).
        Bez tego testu ktoś mógłby przypadkiem zamienić kolejność `except AbortRun: raise` /
        `except Exception:` podczas refaktoru i kill switch przestałby działać w pętli agenta —
        cicho, bez czerwonego testu."""
        tool_call = ToolCall(id="c1", name="aborting", arguments={})
        mock_provider.complete_with_tools.return_value = make_response("", tool_calls=[tool_call])

        def aborting_executor(name, args):
            raise AbortRun("Przerwano przez .run/STOP (graceful stop).")

        with pytest.raises(AbortRun):
            llm.run_agent_loop(
                [LLMMessage.user("test")],
                tools=[Tool("aborting", "Narzędzie zgłaszające kill switch", {})],
                tool_executor=aborting_executor,
            )


class TestPropagacjaBledowNarzedzi:
    """
    AID-48: model musi dostać treść błędu narzędzia, nie stały string.

    Do 2026-08-20 każdy wyjątek zwijał się do "ERROR: Tool execution failed.",
    przez co agent nie odróżniał rate limitu od złego argumentu i pętlił się.
    """

    def _run_with_failing_tool(self, llm, mock_provider, exc: Exception) -> str:
        """Uruchamia jedną iterację pętli z narzędziem, które rzuca `exc`."""
        mock_provider.complete_with_tools.side_effect = [
            make_response("", [ToolCall(id="1", name="broken", arguments={})]),
            make_response("koniec"),
        ]
        def executor(name: str, args: dict) -> str:
            raise exc

        llm.run_agent_loop(
            [LLMMessage.user("start")],
            [Tool(name="broken", description="d", parameters={})],
            executor,
        )
        # Historia trafia do providera przy DRUGIM wywołaniu — stamtąd bierzemy
        # dokładnie to, co realnie zobaczył model po awarii narzędzia.
        second_call_history = mock_provider.complete_with_tools.call_args_list[1].args[0]
        return "\n".join(m.content for m in second_call_history)

    def test_model_widzi_kod_http_i_instrukcje(self, llm, mock_provider):
        exc = RuntimeError("rate limited")
        response = MagicMock()
        response.status_code = 429
        response.text = ""
        exc.response = response

        seen = self._run_with_failing_tool(llm, mock_provider, exc)
        assert "429" in seen
        assert "PRZEJSCIOWY" in seen

    def test_model_nie_dostaje_juz_generycznego_stringa(self, llm, mock_provider):
        seen = self._run_with_failing_tool(llm, mock_provider, ValueError("zle miasto"))
        assert "zle miasto" in seen
        assert "ERROR: Tool execution failed." not in seen

    def test_abortrun_nadal_propaguje(self, llm, mock_provider):
        """Kill switch to sygnał zabicia, nie awaria narzędzia (kontrakt core/AGENTS.md)."""
        mock_provider.complete_with_tools.return_value = make_response(
            "", [ToolCall(id="1", name="broken", arguments={})]
        )

        def executor(name: str, args: dict) -> str:
            raise AbortRun("stop")

        with pytest.raises(AbortRun):
            llm.run_agent_loop(
                [LLMMessage.user("start")],
                [Tool(name="broken", description="d", parameters={})],
                executor,
            )


class TestDynamicznychNarzedzi:
    """AID-50: narzędzia odkrywane w runtime (s03e05 ma tylko /api/toolsearch)."""

    def test_lista_dziala_jak_wczesniej(self, llm, mock_provider):
        """Wsteczna zgodność — istniejące zadania przekazują listę."""
        mock_provider.complete_with_tools.return_value = make_response("gotowe")
        tools = [Tool(name="a", description="d", parameters={})]

        result = llm.run_agent_loop([LLMMessage.user("x")], tools, lambda n, a: "")

        assert result == "gotowe"
        assert mock_provider.complete_with_tools.call_args.args[1] == tools

    def test_narzedzie_dodane_w_trakcie_trafia_do_modelu(self, llm, mock_provider):
        """
        Sedno AID-50: narzędzie odkryte w iteracji 1 musi być widoczne w iteracji 2.
        Przy statycznej liście `toolsearch` nie miałby jak nic dołożyć.
        """
        discovered = [Tool(name="search", description="d", parameters={})]

        mock_provider.complete_with_tools.side_effect = [
            make_response("", [ToolCall(id="1", name="search", arguments={})]),
            make_response("koniec"),
        ]

        def executor(name: str, args: dict) -> str:
            discovered.append(Tool(name="maps", description="odkryte", parameters={}))
            return "znalazlem nowe narzedzie"

        llm.run_agent_loop([LLMMessage.user("x")], lambda: discovered, executor)

        first = [t.name for t in mock_provider.complete_with_tools.call_args_list[0].args[1]]
        second = [t.name for t in mock_provider.complete_with_tools.call_args_list[1].args[1]]
        assert first == ["search"]
        assert second == ["search", "maps"]


class TestThinkingPassthrough:
    """
    `thinking` musi dotrzeć do providera każdą ścieżką, nie tylko przez `chat()`.
    Pętla agentowa jest tu najważniejsza — to jedyne miejsce, gdzie myślenie realnie
    się opłaca, a wpięcie w #80 objęło wyłącznie `chat()`.
    """

    def test_structured_forwards_thinking(self, llm, mock_provider):
        class Wynik(BaseModel):
            x: int

        mock_provider.complete_structured.return_value = LLMResponse(
            content='{"x": 1}', model="m", input_tokens=1, output_tokens=1, parsed=Wynik(x=1)
        )
        llm.structured([LLMMessage.user("hi")], Wynik, thinking="high")

        assert mock_provider.complete_structured.call_args.kwargs["thinking"] == "high"

    def test_agent_loop_forwards_thinking_every_iteration(self, llm, mock_provider):
        """Poziom obowiązuje w KAŻDEJ iteracji, nie tylko w pierwszej."""
        tool = Tool(name="t", description="d", parameters={"type": "object", "properties": {}})
        mock_provider.complete_with_tools.side_effect = [
            make_response("", [ToolCall(id="1", name="t", arguments={})]),
            make_response("gotowe"),
        ]
        llm.run_agent_loop([LLMMessage.user("hi")], [tool], lambda n, a: "ok", thinking="medium")

        assert mock_provider.complete_with_tools.call_count == 2
        for call in mock_provider.complete_with_tools.call_args_list:
            assert call.kwargs["thinking"] == "medium"

    def test_none_is_not_forwarded_as_a_level(self, llm, mock_provider):
        """`None` ma zostawić domyślne dostawcy, a nie zostać zinterpretowane jako 'none'."""
        mock_provider.complete.return_value = make_response("ok")
        llm.chat([LLMMessage.user("hi")])

        assert mock_provider.complete.call_args.kwargs["thinking"] is None


def test_tool_call_turn_is_recorded_even_without_text(llm, mock_provider):
    """
    Regresja zmierzona 2026-08-24: przy włączonym myśleniu tura z wywołaniem narzędzia
    zwraca `['thinking', 'tool_use']` — bez bloku tekstowego. Poprzedni warunek
    `if last_content:` pomijał wtedy zapis tury asystenta, a że historia jest spłaszczona
    do tekstu (AID-55) i nie niesie bloków `tool_use`, model nie widział śladu własnego
    wywołania i powtarzał je. Przebieg potrafił zużyć wszystkie iteracje i zwrócić "".
    """
    tool = Tool(name="dodaj", description="d", parameters={"type": "object", "properties": {}})
    mock_provider.complete_with_tools.side_effect = [
        make_response("", [ToolCall(id="1", name="dodaj", arguments={"a": 1})]),
        make_response("wynik to 2"),
    ]
    llm.run_agent_loop([LLMMessage.user("policz")], [tool], lambda n, a: "2", thinking="low")

    historia = mock_provider.complete_with_tools.call_args_list[1].args[0]
    role_asystenta = [m for m in historia if m.role == "assistant"]
    assert role_asystenta, "tura asystenta zniknęła z historii — model nie zobaczy, że wołał narzędzie"
    assert "dodaj" in role_asystenta[0].content
