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
- `core/observability/decorators.py`: `@langfuse_observe()`, `propagate_attrs()`,
  `langfuse_tool_observation()`.
- `core/observability/prompts.py`: `sync_prompt()`/`get_prompt_ref()` — rejestr promptów.
- Rejestr promptów per-zadanie: `tasks/sXXeYY_*/prompts.py` + stan synchronizacji
  (`.langfuse-prompt-state.json`, gitignored — lokalny cache SHA-256, nie źródło prawdy).

## Local Contracts

### Podział ról — nie zastępują się
- **Logfire** = trace'y, spany, telemetria infrastruktury (czas, błędy, kill switch).
  Możliwości promptowe leżą i kwiczą — nieużywane do niczego związanego z promptami.
- **Langfuse** = warstwa promptowa: rejestr, wersjonowanie, porównywanie, A/B, generacje
  LLM linkowane do wersji promptu. To narzędzie do rzeźbienia poleceń dla LLM-ów, nie
  ogólna telemetria.
- Każde nowe wywołanie LLM w S03+ MUSI mieć: span w Logfire (`logfire.span`) ORAZ
  generację w Langfuse z opcjonalnie podpiętą wersją promptu (`prompt_name=` kwarg na
  `chat()`/`structured()`/`run_agent_loop()`) — działa dla wszystkich trzech od
  2026-08-16 (patrz „Znany dług" niżej, zamknięty).

### Scentralizowany punkt podpięcia
Lekcja S03E01 (sekcja „Zasady monitorowania"): *„U ich podstaw stoi konieczność
podłączenia się pod wszystkie interakcje z LLM API oraz wywołania narzędzi. Dobrze jest
więc na etapie planowania architektury ułożyć te elementy tak, aby były możliwe
scentralizowane."* Ten punkt to `core/llm/middleware.py` — łańcuch
`RateLimitMiddleware → CostTrackMiddleware → ProviderCallMiddleware`
(`core/llm/client.py:40-46`).

**Znany dług — zamknięty 2026-08-16 (`feat/core-observability-langfuse`, przed s03e01).**
Do tej daty `chat()` (`client.py:62`) szedł przez `self._chain.handle(...)`, ale
`structured()` i `run_agent_loop()` wołały `self._provider` bezpośrednio — omijały cały
łańcuch, więc żadna generacja z tych dwóch ścieżek nie trafiała do Langfuse ani do
`CostTrackMiddleware`. Fix nie był przepięciem jednej linii: `LLMProvider.complete_structured`
w ogóle nie zwracał liczników tokenów, więc zmiana dotknęła ABC (`core/llm/base.py`) +
cztery adaptery + `ProviderCallMiddleware`. Kształt rozwiązania:
- `LLMResponse` (`core/llm/types.py`) dostało pole `parsed: BaseModel | None` — structured
  output przechodzi przez ten sam łańcuch co `complete()`, `content` niesie JSON do
  podglądu, `parsed` niesie sparsowaną instancję schematu.
- `complete_structured()` w ABC i wszystkich czterech adapterach zwraca teraz
  `LLMResponse`, nie goły `T` — `LLMClient.structured()` rozpakowuje `.parsed` z powrotem.
- `ProviderCallMiddleware.handle()` dispatchuje po `kwargs["schema"]`/`kwargs["tools"]`
  (popowane przed przekazaniem do adaptera) zamiast zawsze wołać `complete()`.
- `CostTrackMiddleware` i `ProviderCallMiddleware` pozostają rozdzielone (enrichment vs.
  transport) — celowo, patrz sekcja „Async" niżej.

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
(`core/observability/decorators.py`) istniał od dawna, ale nigdy nie był wywoływany —
podpięty w `BaseTask.run()` 2026-08-16 (`session_id = f"{task_name}-{timestamp}"`, patrz
`core/tasks/base.py`). Wywołania narzędzi w `run_agent_loop()` dostają od tej samej daty
observation Langfuse typu `Tool` (`langfuse_tool_observation()`, `core/observability/decorators.py`),
nie tylko span Logfire jak wcześniej.

### Rejestr promptów — jednostronna synchronizacja kod → Langfuse
Lekcja S03E01: *„wystarczającym rozwiązaniem może okazać się jednostronna
synchronizacja, w przypadku której zmiany po stronie aplikacji są odzwierciedlane np.
w Langfuse. (…) największa wartość i tak wiąże się z możliwością łatwej oceny bieżącego
stanu."* **Nie** pobieramy promptów z Langfuse w runtime — kod jest jedynym źródłem
prawdy, Langfuse jest tylko rejestrem do porównywania.

Mechanizm (wzorzec `4th-devs/03_01_observability/src/core/tracing/prompts.ts`,
przepisany na Python — reguła „4th-devs najpierw"):

1. prompt w kodzie zadania (`tasks/sXXeYY_*/prompts.py`) — jedyne źródło prawdy,
2. zadanie woła `sync_prompt(name, content)` raz przy starcie: `SHA-256(treść)` →
   porównanie ze stanem w `.langfuse-prompt-state.json` → push do Langfuse **tylko jeśli
   treść się zmieniła** → zapis `{content_hash, version}`, zwraca `PromptRef`,
3. zadanie przekazuje `prompt_name=name` do `llm.chat()`/`.structured()`/`run_agent_loop()`
   — `CostTrackMiddleware` sam wyszukuje referencję (`get_prompt_ref()`) i podpina ją pod
   generację (`start_observation(prompt=...)`),
4. brak kluczy Langfuse / błąd sieci → `PromptRef.is_fallback=True`, zadanie leci dalej.
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
