---
id: r14
severity: ERROR
scope: "core/hub/**, tasks/**/solution.py"
zrodlo: "R7 (.claude/review-rules.md, 'nowa — z obserwacji')"
---

# r14 — Obsługa wyjątków HTTP zawężona do udokumentowanego kodu

Wymagania:

- `except httpx.HTTPStatusError` musi sprawdzać konkretny kod, dla którego zachowanie
  jest udokumentowane; pozostałe re-raise.
- `response.json()` na ścieżce błędu zawsze w `try/except ValueError` z sensownym
  fallbackiem.
- Wartości liczbowe z ciała odpowiedzi (`retry_after`) parsowane defensywnie: brak
  klucza, typ nienumeryczny, wartość ujemna.
- `@retry` z tenacity bez `reraise=True` podmienia oryginalny wyjątek na `RetryError` —
  wywołujący łapiący `HTTPStatusError` przestaje działać. Albo `reraise=True`, albo jawna
  obsługa `RetryError` z rozpakowaniem `last_attempt.exception()`.

> **Uwaga z historii:** naruszenie potwierdzone 14.08.2026 —
> `tasks/s02e03_failure/solution.py:270-271`:
> `except httpx.HTTPStatusError as exc: return exc.response.json()`, bez sprawdzenia
> `status_code` i bez `try/except ValueError`. 401/403/500 traktowane jak feedback
> protokołu; niepoprawny JSON w ciele wywala `ValueError`. Uwaga #1 z PR #56,
> nienaprawiona. `tasks/s02e04_mailbox/solution.py:165` flagowane jako "do sprawdzenia" —
> szerokie łapanie może tam być celowe, ale wymaga jawnego ograniczenia do
> udokumentowanych kodów. Wzorzec wracał w PR #51, #56, #57; domknięty w #51 i #57. Status
> bieżący do zweryfikowania przez `contract-audit`.

## Jak zgłaszać
`ERROR` — nienegocjowalne. PR: `BLOCKER`. Poza PR-em: issue Linear `type/bug` +
`area/core` lub `area/tasks` zależnie od pliku, priorytet Wysoki (błąd cichy — 401/403/500
mylone z feedbackiem protokołu kursu).
