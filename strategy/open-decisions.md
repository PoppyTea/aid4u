# Otwarte decyzje — bez miejsca w roadmapie

## Purpose
Pytania rozstrzygalne międzysezonowo, warte zapisania i pamiętania, ale bez konkretnego
przystanku w `tasks/sXX/requirements/` gdzie by naturalnie wylądowały. Różnica względem
długu w Linear: te pozycje nie blokują żadnego konkretnego epizodu (brak labela `gate/*`)
i nie mają przypisanego sezonu — czekają na świadomą decyzję przed większą inwestycją
czasu w dany temat, nie na wykonanie.

## Ownership
Ten plik. Gdy pytanie dostaje odpowiedź, przenieś rozstrzygnięcie do właściwego
dokumentu docelowego (np. `strategy/secrets-management.md`, `strategy/observability.md`)
i usuń wpis stąd — nie zostawiaj martwych pytań z dopiskiem „rozstrzygnięte gdzie indziej".

## Local Contracts
- Każdy wpis: pytanie w jednym zdaniu, kontekst czemu nie jest pilne, kontekst czemu
  warto rozstrzygnąć zanim inwestycja czasu urośnie.

## Work Guidance
(brak — dopisuj wpisy w miarę pojawiania się, bez osobnego rytuału)

## Verification
(none)

---

## Otwarte pytania

### Langfuse: self-hosted (VPS) czy dalej free tier w chmurze?
Zgłoszone 2026-08-16. Free tier w chmurze jest realnie toporny w działaniu (potwierdzone
w praktyce, nie tylko z dokumentacji). Self-hosted na VPS (mamy już `deploy/` i tunel z
`s01e03_proxy`) mógłby to rozwiązać, ale to osobna decyzja infrastrukturalna, nie coś do
rozstrzygnięcia mimochodem przy pierwszym zadaniu, które używa Langfuse na poważnie.
**Rozstrzygnąć przed większą inwestycją czasu w Langfuse** (np. przed dodaniem
scores/datasets, przed S04) — im więcej zadań opiera się o dzisiejszą konfigurację, tym
droższa migracja, tak samo jak przy decyzji `pydantic-ai` vs własny `core/llm/`
(`tasks/s03/requirements/core-stack-decision.md`).

### Async w `core/llm/` — kiedy?
Zgłoszone 2026-08-16. Dziś `core/llm/` i `core/hub/` są w pełni synchroniczne. Audyt per
epizod S03 (`strategy/observability.md`, sekcja „Async") nie znalazł żadnego epizodu,
który by tego wymagał — e04 jest jedynym punktem tarcia i ma trywialne obejście
(handler FastAPI jako `def`, nie `async def`). Nie konwertować teraz. Rewizja tej decyzji
zasadna, jeśli: (a) pojawi się zadanie z realnie równoległymi wywołaniami LLM na dużą
skalę (nie 3 batche jak e01, ale dziesiątki/setki), (b) `core/server/factory.py` zacznie
obsługiwać wiele jednoczesnych żądań na produkcji, nie tylko lokalny tunel do jednego
epizodu. Przy naprawie łańcucha middleware (przed s03e01) logika wzbogacania zdarzenia
jest już rozdzielana od wywołania transportu — więc koszt późniejszej konwersji na
`ahandle()` zostaje niski niezależnie od tego, kiedy do niej dojdzie.
