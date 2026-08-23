"""
Poziomy „myślenia" — jedno słownictwo provider-agnostyczne.

Każdy dostawca nazywa to inaczej i przyjmuje inny kształt danych: Anthropic liczy
`budget_tokens`, OpenAI ma nazwane `reasoning_effort`, Gemini ma **dwa** wykluczające się
kontrakty zależne od rodziny modelu. Ten moduł jest jedynym miejscem, które o tym wie —
adaptery pytają go o gotową konfigurację, a reszta warstwy operuje wyłącznie na
`ThinkingLevel`.

Drabina jest ta sama, co u OpenAI (`ReasoningEffort`), bo jako jedyny dostawca ma nazwane
poziomy pokrywające całą skalę. Anthropic operuje wyłącznie liczbą tokenów, więc jego
poziomy wyprowadzamy jako **procent budżetu odpowiedzi** — patrz `BUDGET_PCT`.

## Co realnie wspiera który dostawca (zmierzone 2026-08-23 żywymi wywołaniami)

| poziom    | Anthropic | OpenAI¹ | Gemini 2.5 | Gemini 3.x flash | Gemini 3.x pro |
|-----------|-----------|---------|------------|------------------|----------------|
| `none`    | disabled  | `none`  | budget=0   | budget=0         | **400**        |
| `minimal` | budżet    | tak     | budżet     | **400**          | **400**        |
| `low`     | budżet    | tak     | budżet     | `level=low`      | `level=low`    |
| `medium`  | budżet    | tak     | budżet     | `level=medium`   | `level=medium` |
| `high`    | budżet    | tak     | budżet     | `level=high`     | `level=high`   |
| `xhigh`   | budżet    | tak     | budżet     | **brak**         | **brak**       |
| `max`     | budżet    | tak     | budżet     | **brak**         | **brak**       |

¹ OpenAI wg deklaracji SDK (`openai.types.shared.ReasoningEffort`), **nie zweryfikowane
realnym wywołaniem** — klucz projektu nie ma środków (`429: You have no credits
remaining`), więc żadne wywołanie do OpenAI nie przechodzi niezależnie od parametrów.

Pułapki, na które nie wpadniesz z samej dokumentacji:
- `ThinkingLevel.MINIMAL` **istnieje w enumie SDK Gemini**, ale modele odrzucają go
  czterystką („Thinking level MINIMAL is not supported"). Obecność w enumie nie oznacza
  wsparcia.
- Gemini 3.x przyjmuje `thinking_budget=0` mimo że steruje się go `thinking_level` —
  czyli `none` jest osiągalne. Wyjątkiem są modele `pro`, które odmawiają wprost
  („This model only works in thinking mode").
- Anthropic wymaga `budget_tokens >= 1024` **i** `max_tokens > budget_tokens`. Przy
  domyślnym `max_tokens=1024` żaden poziom poza `none` nie jest osiągalny — stąd bramka
  z konkretną liczbą w komunikacie zamiast cichego przycięcia.
"""

from __future__ import annotations

from typing import Literal, get_args

ThinkingLevel = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]

THINKING_LEVELS: tuple[ThinkingLevel, ...] = get_args(ThinkingLevel)
"""Drabina rosnąco. Kolejność ma znaczenie — komunikaty błędów cytują ją w tej postaci."""

BUDGET_PCT: dict[str, float] = {
    "minimal": 0.10,
    "low": 0.20,
    "medium": 0.40,
    "high": 0.60,
    "xhigh": 0.70,
    "max": 0.80,
}
"""
Poziom → udział budżetu odpowiedzi przeznaczony na myślenie. Dotyczy dostawców, którzy
nie mają nazwanych poziomów (Anthropic, Gemini 2.5). `max` to 80%, nie 100% — model musi
mieć z czego napisać właściwą odpowiedź po zakończeniu myślenia.
"""

ANTHROPIC_MIN_BUDGET = 1024
"""Minimum wymuszone przez API (zmierzone: 1023 → 400, 1024 → OK)."""

GEMINI_25_MAX_BUDGET = 24576
"""Maksimum dla rodziny 2.5 (zmierzone: 24576 → OK, 30000 → 400)."""

_GEMINI_NAMED_LEVELS = frozenset({"low", "medium", "high"})
"""Poziomy, które rodzina 3.x przyjmuje jako `thinking_level`. `minimal` NIE działa."""


class ThinkingNotSupported(ValueError):
    """
    Dany poziom myślenia jest nieosiągalny dla tego modelu albo tej konfiguracji.

    Osobny typ, a nie gołe `ValueError`, żeby wywołujący mógł odróżnić „ten model tego nie
    umie" od „przekazałeś bzdurę" i ewentualnie zejść poziom niżej zamiast przerywać.
    """


def validate(level: str) -> ThinkingLevel:
    """Sprawdza, czy `level` jest na drabinie. Zwraca go, żeby dało się użyć w wyrażeniu."""
    if level not in THINKING_LEVELS:
        raise ValueError(
            f"Nieznany poziom myślenia: {level!r}. Dopuszczalne: {', '.join(THINKING_LEVELS)}."
        )
    return level  # type: ignore[return-value]


def _budget(level: ThinkingLevel, total_tokens: int) -> int:
    """Przelicza poziom na liczbę tokenów myślenia jako procent budżetu odpowiedzi."""
    return int(total_tokens * BUDGET_PCT[level])


def anthropic_thinking(level: ThinkingLevel, max_tokens: int) -> dict[str, object]:
    """
    Buduje wartość parametru `thinking` dla `messages.create`.

    Podnosi `ThinkingNotSupported`, gdy `max_tokens` jest za małe, by pomieścić budżet —
    z konkretną liczbą do ustawienia, bo sama informacja „za mało" nie mówi, ile trzeba.
    """
    validate(level)
    if level == "none":
        return {"type": "disabled"}

    budget = max(_budget(level, max_tokens), ANTHROPIC_MIN_BUDGET)
    if budget >= max_tokens:
        raise ThinkingNotSupported(
            f"Poziom myślenia {level!r} wymaga budżetu {budget} tokenów, a `max_tokens` "
            f"wynosi {max_tokens}. Anthropic wymaga `max_tokens > budget_tokens` oraz "
            f"budżetu >= {ANTHROPIC_MIN_BUDGET}. Ustaw `max_tokens` na co najmniej "
            f"{budget + 1} albo zejdź na poziom 'none'."
        )
    return {"type": "enabled", "budget_tokens": budget}


def openai_reasoning_effort(level: ThinkingLevel) -> ThinkingLevel:
    """
    Mapuje poziom na `reasoning_effort`. Odwzorowanie jest tożsamościowe — nasza drabina
    została celowo zapożyczona z `openai.types.shared.ReasoningEffort`.

    Zwraca `ThinkingLevel` (a nie `str`), bo SDK oczekuje tam swojego `Literal`-a;
    `str` nie pasuje do żadnego przeciążenia i cała sygnatura wywołania się rozjeżdża.
    Test `test_matches_sdk_literal_exactly` pilnuje, żeby oba literały się nie rozeszły.
    """
    return validate(level)


def gemini_thinking(level: ThinkingLevel, model: str, max_output_tokens: int):
    """
    Buduje `types.ThinkingConfig` właściwy dla rodziny modelu.

    Rodzina 2.5 steruje myśleniem budżetem tokenów, rodzina 3.x — nazwanym poziomem;
    **zmieszanie obu w jednym zapytaniu to 400**, więc zwracany obiekt zawsze ustawia
    dokładnie jedno pole.
    """
    from google.genai import types

    validate(level)
    is_25 = model.startswith("gemini-2.")

    if level == "none":
        if not is_25 and _is_gemini_pro(model):
            raise ThinkingNotSupported(
                f"Model {model!r} nie pozwala wyłączyć myślenia ('This model only works in "
                "thinking mode'). Najniższy osiągalny poziom to 'low'."
            )
        return types.ThinkingConfig(thinking_budget=0)

    if is_25:
        budget = min(_budget(level, max_output_tokens), GEMINI_25_MAX_BUDGET)
        return types.ThinkingConfig(thinking_budget=budget)

    if level not in _GEMINI_NAMED_LEVELS:
        raise ThinkingNotSupported(
            f"Rodzina Gemini 3.x nie wspiera poziomu {level!r} — dopuszczalne to "
            f"{', '.join(sorted(_GEMINI_NAMED_LEVELS))} albo 'none'. Uwaga: 'minimal' "
            "istnieje w enumie SDK, ale modele odrzucają go czterystką."
        )
    return types.ThinkingConfig(thinking_level=level)


def _is_gemini_pro(model: str) -> bool:
    """Czy to model z rodziny `pro` — jedyna, która wymusza włączone myślenie."""
    return "-pro" in model
