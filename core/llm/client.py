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
from core.llm.types import LLMMessage, LLMResponse, Tool

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
    ) -> str:
        """Proste wywołanie tekstowe. Zwraca string."""
        response = self._chain.handle(messages, system=system, max_tokens=max_tokens)
        return response.content

    def structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        """Wywołanie ze strukturyzowanym wyjściem. Zwraca instancję Pydantic modelu."""
        return self._provider.complete_structured(messages, schema, system=system)

    # ─── Pętla agentowa ──────────────────────────────────────────────────────

    def run_agent_loop(
        self,
        initial_messages: list[LLMMessage],
        tools: list[Tool],
        tool_executor: Callable[[str, dict[str, Any]], str],
        *,
        system: str | None = None,
        max_iterations: int = 10,
    ) -> str:
        """
        Pętla agentowa z function calling.

        Args:
            initial_messages: Wiadomości startowe
            tools: Definicje narzędzi dostępnych dla modelu
            tool_executor: Funkcja wykonująca narzędzia: (name, args) -> str
            system: System prompt
            max_iterations: Zabezpieczenie przed nieskończoną pętlą

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

        with logfire.span("agent_loop", tools=[t.name for t in tools]):
            for iteration in range(max_iterations):
                logfire.info(f"Agent iteration {iteration + 1}/{max_iterations}")

                response = self._provider.complete_with_tools(
                    history, tools, system=system
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
                    with logfire.span(f"tool.{tool_call.name}", args=tool_call.arguments):
                        try:
                            result = tool_executor(tool_call.name, tool_call.arguments)
                        except Exception as e:
                            result = f"ERROR: {e}"
                            logfire.exception(f"Tool {tool_call.name} failed")

                        logfire.info(f"Tool {tool_call.name} result", result=result[:200])
                        history.append(
                            LLMMessage.user(f"[Tool result: {tool_call.name}]\n{result}")
                        )

            logfire.warning(f"Agent loop reached max_iterations={max_iterations}")
            return last_content
