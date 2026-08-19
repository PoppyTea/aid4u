---
id: r15
severity: WARNING
scope: "core/hub/client.py, **/*.py (metody dekorowane @retry)"
zrodlo: "R8 (.claude/review-rules.md, 'nowa — z obserwacji')"
---

# r15 — Spójność `reraise` w metodach dekorowanych `@retry`

`@retry` z tenacity bez `reraise=True` po wyczerpaniu prób rzuca `tenacity.RetryError`,
nie oryginalny wyjątek. Wywołujący, który łapie `httpx.HTTPStatusError` albo
`httpx.TransportError`, przestaje działać — po cichu: nie ma błędu składni, nie ma
ostrzeżenia, jest tylko obsługa, która nagle nic nie łapie.

Wymóg: **wszystkie** metody z `@retry` w jednej klasie mają ten sam kontrakt wyjątków.
Albo wszędzie `reraise=True`, albo wszędzie jawna obsługa `RetryError` z rozpakowaniem
`last_attempt.exception()` — nie mieszać.

> **Uwaga z historii:** niespójność potwierdzona 14.08.2026 w `core/hub/client.py`:
> `_get_data_plain` (154), `_get_data_503_tolerant` (167), `get_public` (181) — brak
> `reraise=True`; `post_api` (213) — jest (poprawka PR #57). Czy trzy pozostałe metody
> realnie gryzą zależy od tego, czy jakiś wywołujący łapie wyjątki `httpx` wokół
> `get_data` — sprawdzić `rg -n "get_data|get_public" -B2 -A6 tasks/ core/` przed
> naprawą. To jest dokładnie przykład wzorca opisanego w r16
> (`contract-audit/r16-fix-propagation-gaps.md`) — jedna metoda naprawiona, siostrzane
> nie.

## Jak zgłaszać
PR-review dla nowego/zmienionego kodu `@retry`. Poza PR-em: `contract-audit` zgłasza jako
rozjazd propagacji (r16) z odciskiem `core/hub/client.py::r15::<metoda>`.
