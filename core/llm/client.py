"""
Facade pattern — LLMClient.

Jedno miejsce dostępu do LLM dla wszystkich zadań.
Ukrywa: wybór adaptera, middleware pipeline, retry, cost tracking, structured output.

⚠️  Model przekazujesz przez create_provider() w run.py.
    Domyślny: gemini-2.5-flash — NIE zmieniaj na gpt-4o ani modele gemini-2.0/1.5 (wycofane).

Kod w zadaniu:
    response = self.llm.chat([LLMMessage.user("Pytanie")])
    data = self.llm.structured(messages, MySchema)
    result = self.llm.run_agent_loop(messages, tools, executor)
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from core.llm.base import LLMProvider
from core.llm.middleware import CostTrackMiddleware, ProviderCallMiddleware, RateLimitMiddleware
from core.llm.tool_errors import format_tool_error
from core.llm.types import LLMMessage, Tool
from core.observability.decorators import langfuse_tool_observation
from core.runtime import AbortRun, check_abort, truncate_tool_result

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Facade nad LLMProvider + middleware pipeline.

    Używaj tej klasy w zadaniach — nigdy bezpośrednio adapterów.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

        # Budowanie łańcucha: RateLimit → CostTrack → ProviderCall
        rate_limit = RateLimitMiddleware()
        cost_track = CostTrackMiddleware()
        provider_call = ProviderCallMiddleware(provider)

        rate_limit.set_next(cost_track).set_next(provider_call)
        self._chain = rate_limit

    @property
    def model(self) -> str:
        return self._provider.model_name

    # ─── Podstawowe interfejsy ────────────────────────────────────────────────

    def chat(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        prompt_name: str | None = None,
    ) -> str:
        """
        Proste wywołanie tekstowe. Zwraca string.

        `prompt_name`: nazwa promptu zarejestrowana wcześniej przez
        `core.observability.prompts.sync_prompt()` — jeśli podana, generacja
        w Langfuse zostaje podpięta pod tę wersję (patrz `strategy/observability.md`).
        Opcjonalne — brak podania po prostu nie linkuje generacji do żadnego promptu.
        """
        response = self._chain.handle(
            messages, system=system, max_tokens=max_tokens, prompt_name=prompt_name
        )
        return response.content

    def structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        system: str | None = None,
        prompt_name: str | None = None,
    ) -> T:
        """
        Wywołanie ze strukturyzowanym wyjściem. Zwraca instancję Pydantic modelu.

        Idzie przez ten sam łańcuch middleware co `chat()` (RateLimit → CostTrack →
        ProviderCall) — do 2026-08-16 wołało `self._provider` bezpośrednio, więc
        cost-tracking i generacje Langfuse nigdy nie widziały structured output.
        `schema=` w kwargs sygnalizuje `ProviderCallMiddleware`, żeby wywołać
        `complete_structured()` zamiast `complete()` — patrz `middleware.py`.
        `prompt_name`: patrz docstring `chat()`.
        """
        response = self._chain.handle(
            messages, system=system, schema=schema, prompt_name=prompt_name
        )
        if not isinstance(response.parsed, schema):
            raise TypeError(
                f"Provider zwrócił nieoczekiwany typ dla structured output: "
                f"{type(response.parsed).__name__}, oczekiwano {schema.__name__}."
            )
        return response.parsed

    # ─── Pętla agentowa ──────────────────────────────────────────────────────

    def run_agent_loop(
        self,
        initial_messages: list[LLMMessage],
        tools: list[Tool] | Callable[[], list[Tool]],
        tool_executor: Callable[[str, dict[str, Any]], str],
        *,
        system: str | None = None,
        max_iterations: int = 10,
        prompt_name: str | None = None,
    ) -> str:
        """
        Pętla agentowa z function calling.

        Args:
            initial_messages: Wiadomości startowe
            tools: Definicje narzędzi dostępnych dla modelu — lista albo **funkcja
                bez argumentów zwracająca listę**, wywoływana na początku KAŻDEJ
                iteracji. Wariant z funkcją obsługuje narzędzia odkrywane w runtime
                (`s03e05` ma tylko `/api/toolsearch`, które zwraca 3 dopasowania na
                zapytanie — statyczna lista nie istnieje). Zadanie trzyma odkryte
                narzędzia po swojej stronie i zwraca aktualny stan.
            tool_executor: Funkcja wykonująca narzędzia: (name, args) -> str
            system: System prompt
            max_iterations: Zabezpieczenie przed nieskończoną pętlą
            prompt_name: patrz docstring `chat()` — linkuje każdą generację
                iteracji do wersji promptu w rejestrze.

        Returns:
            Ostateczna odpowiedź tekstowa modelu (po zakończeniu wywołań narzędzi)

        Przykład:
            def executor(name: str, args: dict) -> str:
                if name == "search":
                    return search_web(args["query"])
                raise ValueError(f"Unknown tool: {name}")

            result = llm.run_agent_loop(messages, tools, executor)
        """
        import logfire

        history = list(initial_messages)
        last_content = ""
        resolve_tools = tools if callable(tools) else (lambda: tools)
        seen_tool_names: set[str] = set()

        with logfire.span("agent_loop"):
            for iteration in range(max_iterations):
                check_abort()

                # Lista narzędzi jest ustalana CO ITERACJĘ, nie raz na starcie —
                # inaczej narzędzie odkryte w trakcie runu (toolsearch) nigdy nie
                # trafiłoby do modelu.
                current_tools = list(resolve_tools())
                new_names = {t.name for t in current_tools} - seen_tool_names
                if new_names:
                    seen_tool_names |= new_names
                    logfire.info(
                        "Agent tools available", tools=sorted(seen_tool_names), added=sorted(new_names)
                    )

                logfire.info(f"Agent iteration {iteration + 1}/{max_iterations}")

                # `tools=` w kwargs kieruje ProviderCallMiddleware do complete_with_tools()
                # zamiast complete() — patrz middleware.py. Każda iteracja pętli dostaje
                # teraz cost-tracking i generację Langfuse (do 2026-08-16 to wywołanie
                # omijało łańcuch middleware).
                response = self._chain.handle(
                    history, system=system, tools=current_tools, prompt_name=prompt_name
                )
                last_content = response.content

                if not response.has_tool_calls:
                    logfire.info("Agent finished — no more tool calls")
                    return last_content

                # Dodaj odpowiedź asystenta do historii
                if last_content:
                    history.append(LLMMessage.assistant(last_content))

                # Wykonaj narzędzia i dodaj wyniki do historii
                for tool_call in response.tool_calls:
                    with (
                        logfire.span(f"tool.{tool_call.name}", args=tool_call.arguments),
                        langfuse_tool_observation(
                            tool_call.name, input=tool_call.arguments
                        ) as set_langfuse_output,
                    ):
                        check_abort()
                        try:
                            result = tool_executor(tool_call.name, tool_call.arguments)
                        except AbortRun:
                            # Kill switch, nie awaria narzędzia — propaguj, nie połykaj.
                            raise
                        except Exception as exc:
                            # Model dostaje typ błędu, kod HTTP i instrukcję co dalej —
                            # bez tego nie odróżnia "rate limit, poczekaj" od "zły
                            # argument, popraw" i pętli się na tym samym wywołaniu
                            # (patrz core/llm/tool_errors.py).
                            result = truncate_tool_result(
                                format_tool_error(tool_call.name, exc)
                            )
                            logfire.exception(f"Tool {tool_call.name} failed")
                        else:
                            # Warstwa 2 (per-call): ucina nienormalnie duży wynik zanim
                            # zaleje kontekst — np. `cat` dużego pliku (patrz core/AGENTS.md).
                            result = truncate_tool_result(result)

                        logfire.info(f"Tool {tool_call.name} result", result=result[:200])
                        set_langfuse_output(result)
                        history.append(
                            LLMMessage.user(f"[Tool result: {tool_call.name}]\n{result}")
                        )

            logfire.warning(f"Agent loop reached max_iterations={max_iterations}")
            return last_content
