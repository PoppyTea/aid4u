# Warstwa obserwacji — Logfire + Langfuse

## Purpose
Kontrakt scentralizowanej obserwacji LLM/narzędzi w tym repo: podział ról między
Logfire i Langfuse, hierarchia zdarzeń, rejestr promptów, i decyzja o async. Powstał
przy starcie S03 (2026-08-16), gdy pokrycie generacji LLM wynosiło zero — jedyny
`@langfuse_observe()` w repo siedział na `_get_data_plain` (`core/hub/client.py:166`),
w miejscu bez żadnego LLM. Lekcja `s03e01-obserwowanie-i-ewaluacja` jest źródłem
większości decyzji poniżej, cytowana z numerem sekcji tamtej lekcji.

## Ownership
- `core/llm/middleware.py`: łańcuch, przez który MUSI przechodzić każde wywołanie LLM.
- `core/observability/decorators.py`: `@langfuse_observe()`, `propagate_attrs()`.
- Rejestr promptów per-zadanie: `tasks/sXXeYY_*/prompts.py` + stan synchronizacji
  (`.langfuse-prompt-state.json`, gitignored — lokalny cache SHA-256, nie źródło prawdy).

## Local Contracts

### Podział ról — nie zastępują się
- **Logfire** = trace'y, spany, telemetria infrastruktury (czas, błędy, kill switch).
  Możliwości promptowe leżą i kwiczą — nieużywane do niczego związanego z promptami.
- **Langfuse** = warstwa promptowa: rejestr, wersjonowanie, porównywanie, A/B, generacje
  LLM linkowane do wersji promptu. To narzędzie do rzeźbienia poleceń dla LLM-ów, nie
  ogólna telemetria.
- Każde nowe wywołanie LLM w S03+ MUSI mieć: span w Logfire (już działa przez
  `logfire.span`) ORAZ generację w Langfuse z podpiętą wersją promptu (dziś nie działa
  dla `.structured()`/`run_agent_loop()` — patrz niżej).

### Scentralizowany punkt podpięcia
Lekcja S03E01 (sekcja „Zasady monitorowania"): *„U ich podstaw stoi konieczność
podłączenia się pod wszystkie interakcje z LLM API oraz wywołania narzędzi. Dobrze jest
więc na etapie planowania architektury ułożyć te elementy tak, aby były możliwe
scentralizowane."* Ten punkt to `core/llm/middleware.py` — łańcuch
`RateLimitMiddleware → CostTrackMiddleware → ProviderCallMiddleware`
(`core/llm/client.py:40-46`).

**Znany dług (do zamknięcia przed S03e01):** `chat()` (`client.py:62`) idzie przez
`self._chain.handle(...)`, ale `structured()` (`:73`) i `run_agent_loop()` (`:117`)
wołają `self._provider` bezpośrednio — omijają cały łańcuch, więc żadna generacja z tych
dwóch ścieżek nie trafia do Langfuse ani do `CostTrackMiddleware`. Fix nie jest
przepięciem jednej linii: `LLMProvider.complete_structured` w ogóle nie zwraca liczników
tokenów (ABC `core/llm/base.py:41-48`), więc trzeba dotknąć ABC + cztery adaptery +
`ProviderCallMiddleware`.

### Hierarchia zdarzeń (Langfuse)
Z lekcji S03E01, siedem typów, wszystkie uniwersalne:

| Typ | Znaczenie w tym repo |
|---|---|
| `Session` | jedno uruchomienie `run.py solve sXXeYY` |
| `Trace` | jedno wywołanie `BaseTask.run()` |
| `Span` | pojedynczy krok wewnątrz `solve()` (np. faza batchowania) |
| `Generation` | jedna interakcja z LLM — pełny kontekst + ustawienia + wersja promptu |
| `Agent` | jedna iteracja `run_agent_loop()` |
| `Tool` | jedno wywołanie narzędzia (input/output) |
| `Event` | zdarzenie aplikacji niepowiązane z LLM (np. `cost_alert`) |

Kontekst dołączany do każdego zdarzenia: `userId` (n/d w tym repo — jeden operator),
`sessionId`, `agentId`, `promptVersion`, `tags`. Mechanizm `propagate_attrs()`
(`core/observability/decorators.py:75`) już istnieje, ale **nie jest nigdzie wywoływany**
— podpiąć w `BaseTask.run()`.

### Rejestr promptów — jednostronna synchronizacja kod → Langfuse
Lekcja S03E01: *„wystarczającym rozwiązaniem może okazać się jednostronna
synchronizacja, w przypadku której zmiany po stronie aplikacji są odzwierciedlane np.
w Langfuse. (…) największa wartość i tak wiąże się z możliwością łatwej oceny bieżącego
stanu."* **Nie** pobieramy promptów z Langfuse w runtime — kod jest jedynym źródłem
prawdy, Langfuse jest tylko rejestrem do porównywania.

Mechanizm (wzorzec `4th-devs/03_01_observability/src/core/tracing/prompts.ts`,
przepisany na Python — reguła „4th-devs najpierw"):

1. prompt w kodzie zadania (`tasks/sXXeYY_*/prompts.py`) — jedyne źródło prawdy,
2. przy starcie: `SHA-256(treść)` → porównanie ze stanem w `.langfuse-prompt-state.json`
   → push do Langfuse **tylko jeśli treść się zmieniła** → zapis `{content_hash, version}`,
3. `get_prompt_ref(name) -> PromptRef` zwraca `{name, version}`, podpinane do każdej
   generacji,
4. brak kluczy Langfuse / błąd sieci → `is_fallback=True`, zadanie leci dalej.
   **Observability nigdy nie blokuje zdobycia flagi.**

### Async — decyzja, nie domyślne założenie
`core/llm/` i `core/hub/` są w pełni synchroniczne (`httpx.Client`, nie `AsyncClient`).
Sprawdzone per epizod S03 (2026-08-16): e01 ma 3 batche (async oszczędza sekundy, nie
grosze); e02 to pętla z natury sekwencyjna (rate limiter i tak zabrania równoległości);
e03/e05 nie wołają LLM; e04 to jedyne realne ryzyko — sync `LLMClient` w `async def`
handlerze FastAPI blokowałby event loop, omijane trywialnie (handler jako `def`, FastAPI
sam wrzuca do threadpoola).

**Decyzja: nie konwertujemy teraz.** Ale przy naprawie łańcucha middleware (dług wyżej)
logika wzbogacania zdarzenia (kontekst, metadata, prompt ref) MUSI być rozdzielona od
samego wywołania transportu — żeby przyszłe `ahandle()` mogło ją reużyć zamiast
duplikować. Otwarte pytanie „kiedy async" → `strategy/open-decisions.md`.

## Work Guidance
- Przy dodawaniu nowego wywołania LLM w zadaniu S03+: użyj `llm.structured()`/`chat()`/
  `run_agent_loop()` z `core/llm/client.py` (nigdy SDK bezpośrednio — reguła z
  `core/AGENTS.md`), z promptem zarejestrowanym przez mechanizm wyżej.
- Integrację techniczną z SDK Langfuse dobrze jest oprzeć o analizę kodu źródłowego SDK
  przez agenta kodującego (wskazówka z lekcji S03E01) — notatka z tej analizy jest
  źródłem prawdy przy kolejnych rozszerzeniach, nie trzeba jej odtwarzać za każdym razem.
- Dane użytkowników przechodzące przez observability wymagają anonimizacji (nazwy
  własne, adresy, dane kontaktowe) — w tym repo operator jest jeden i znany, więc ryzyko
  jest niskie, ale zasada obowiązuje jeśli kiedyś dojdą dane osób trzecich.

## Verification
- `uv run pytest tests/core/llm/` — `.structured()` przechodzi przez łańcuch middleware
  i raportuje tokeny.
- Realny przebieg dowolnego zadania S03+ pokazuje w panelu Langfuse: trace zadania,
  generacje z podpiętą wersją promptu, zużycie tokenów. To jest weryfikacja końcowa —
  widoczny wpis w panelu, nie tylko zielone testy (analogia do „flaga z huba" jako
  ostatecznej weryfikacji zadania kursowego).

## Child DOX Index
- None.
