"""
Generyczny klasyfikator treści przez structured output LLM.

Reużywalne poza jednym zadaniem z rozmysłem — pierwszy przypadek użycia to
s01e03 (`tasks/s01e03_proxy/tools.py`, redirect_package): sprawdzenie, czy
treść rozmowy z operatorem wskazuje na niebezpieczny ładunek w konkretnej
paczce. Jedyny sygnał w tym zadaniu to naturalny język rozmowy — API paczek
nie zwraca żadnego pola opisującego zawartość — więc słownikowe skanowanie
słów kluczowych jest zbyt kruche; structured output daje jednoznaczne
tak/nie zamiast parsowania swobodnej odpowiedzi tekstowej.

Idzie przez LLMClient.structured() — zgodne z kontraktem core/AGENTS.md
("wszystkie zewnętrzne wywołania LLM przez core/llm/client.py"), nie jest to
wyjątek jak native_tool_*.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.llm.client import LLMClient
from core.llm.types import LLMMessage

_DEFAULT_SYSTEM_PROMPT = (
    "Jesteś precyzyjnym klasyfikatorem treści. Oceniaj wyłącznie na podstawie "
    "podanego tekstu — nie zgaduj, nie dopowiadaj kontekstu, którego tam nie ma."
)


class ClassificationResult(BaseModel):
    matches: bool = Field(description="Czy treść pasuje do opisanej kategorii.")
    reasoning: str = Field(description="Jednozdaniowe uzasadnienie decyzji.")


def classify(
    llm: LLMClient,
    text: str,
    *,
    category_description: str,
    system: str | None = None,
) -> ClassificationResult:
    """
    Klasyfikuje `text` względem jednej kategorii opisanej w `category_description`.

    Przykład:
        result = classify(
            llm,
            conversation_text,
            category_description=(
                "z treści rozmowy wynika, że paczka PKG123 zawiera niebezpieczny "
                "ładunek (rdzeń reaktora, materiał radioaktywny, paliwo jądrowe)"
            ),
        )
        if result.matches:
            ...
    """
    prompt = f"Oceń, czy poniższa treść pasuje do kategorii: {category_description}\n\nTreść:\n{text}"

    return llm.structured(
        [LLMMessage.user(prompt)],
        ClassificationResult,
        system=system or _DEFAULT_SYSTEM_PROMPT,
    )
