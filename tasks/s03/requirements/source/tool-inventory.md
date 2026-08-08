# S03 — inwentarz narzędzi i tematów (materiał źródłowy)

Pełny raport przygotowany 2026-08-08 (wątek planistyczny s02e05 + przegląd S03).
Destylat operacyjny (checklisty, dług, kolejność) żyje w `../season.md` i
`../s03eXX.md` — ten plik to uzasadnienia i pełny kontekst, czytany selektywnie po
linku, nie w całości przy każdym zadaniu.

## Czym są zadania S03 (przeczytane w całości)

| Ep | Zadanie | Istota | Charakter |
|---|---|---|---|
| s03e01 | `evaluation` | 10 000 plików JSON z sensorów → znajdź anomalie | **Inżynieria kosztu.** Progi deterministycznie, LLM **tylko** do sprzeczności notatka↔dane |
| s03e02 | `firmware` | Zdalny okrojony shell (`POST /api/shell`), uruchom binarkę | **Pętla agentowa** + narzędzie shell + twarda obsługa ban/rate-limit/503 |
| s03e03 | `reactor` | Robot 7×5, omijanie ruchomych bloków | **Czysty algorytm** — LLM praktycznie zbędny |
| s03e04 | `negotiations` | **Ty budujesz narzędzia, ICH agent je wywołuje** | **Publiczny hosting HTTP.** Odpowiedź 4–500 B, agent ma 10 kroków, params w NL |
| s03e05 | `savethem` | Odkrywanie narzędzi przez `/api/toolsearch`, trasa 10×10 pod limitem paliwa i jedzenia | **Dynamiczne narzędzia** + optymalizacja dwuzasobowa |

Odwrócenie ról w s03e04 jest najważniejszą nowością sezonu: przestajesz być autorem agenta,
zostajesz **dostawcą narzędzi ocenianym przez cudzego agenta**. Opis narzędzia staje się
artefaktem krytycznym — to on decyduje o sukcesie, nie Twój kod.

## Narzędzia i rozwiązania — cztery kategorie

### 🔴 KONIECZNIE POTRZEBNE

| Co | Po co | Stan |
|---|---|---|
| **`get_public()` w `HubClient`** | `/dane/sensors.zip` (e01), `/dane/s03e04_csv/` (e04) | ✅ dodane przy okazji `s02e05_drone` (PR `feat/hub-get-consolidation`), obsłuży 3 zadania |
| **Propagacja błędów narzędzi do agenta** | e02 wymaga, by agent **widział** kody ban/rate-limit/503 i reagował | ⚠️ **`run_agent_loop()` połyka wyjątki w stały string `"ERROR: Tool execution failed."`** (`core/llm/client.py`) — model nie dostaje żadnego szczegółu. Obejście ręczne istnieje w s02e04; przy e02 to przestaje być obejściem, a staje się wymogiem |
| **Publiczny endpoint HTTP** | e04 — ich agent musi się do nas dodzwonić | ✅ ngrok 3.39.10 zainstalowany, ścieżka **udowodniona bojowo** w s01e03; `core/server/factory.py`, `deploy/ngrok_tunnel.sh`, wzorzec systemd. ⚠️ deploy na VPS niedokonfigurowany: `VPS_HOST` jest w `.env`, ale `VPS_USER` i `VPS_PATH` **brakuje** |
| **Pipeline dedup + cache + batching** | e01 — 10 000 plików, zadanie *jest* o koszcie | ✅ `LocalCache` (`core/hub/cache.py`) + sprawdzony wzorzec z s02e03 (dedup i filtr przed LLM zbił 2137 linii do 55). `zipfile` w stdlib |
| **Deterministyczna symulacja / planowanie ścieżki** | e03 (7×5, cykliczne bloki) i e05 (10×10, dwa zasoby) | ❌ brak, ale to czysty Python — BFS/DP nad przestrzenią stanów `(pozycja, faza_bloków, paliwo, jedzenie)` |
| **Twardy limit rozmiaru wyniku narzędzia** | ⚠️ **Każda zgłoszona strata $4–$10 w S03 pochodzi z niekontrolowanego wyniku narzędzia zalewającego kontekst.** W e02 `cat cooler.bin` wysadza kontekst — ludzie tracili $5–10 na jednym poleceniu | ✅ dodane przy okazji kill switcha (`feat/killswitch`, `truncate_tool_result()`) — sprawdź czy zmergowane przed startem S03 |
| **Własny rate limiter wychodzący** | e02: shell API ~30 req/min, a 429 prawdopodobnie **przedłuża okno** → naiwne retry pętli się w nieskończoność | ❌ brak dla `/api/*`; `post_api()` ma retry (dodany w s02e04), ale to reakcja, nie prewencja |
| **Blacklist ścieżek wymuszony w KODZIE** | e02: zakaz `/etc`, `/root`, `/proc` + respektowanie `.gitignore`; złamanie = ban i reset VM. Modele łamią to notorycznie | ❌ brak — i **musi być w kodzie narzędzia, nie w promptcie** (staff explicite błogosławi hardcode) |
| **Model klasy Sonnet — ale ostrożnie** | e02 wymaga rozumowania | ✅ mamy, ale patrz ostrzeżenie kosztowe w `community-intel.md` — w **nieosłoniętej** pętli shellowej Sonnet potrafi kosztować $4–7 i i tak nie skończyć, podczas gdy Gemini Flash robi to samo za $0.05 |

### 🟡 NICE TO HAVE

| Co | Po co | Stan |
|---|---|---|
| **Langfuse scores + datasets** | e01 to dosłownie zadanie „evaluation", a lekcja e01 to observability+eval | ⚠️ Langfuse **zainicjalizowany, ale prawie nieużywany** — `@langfuse_observe()` wisi na **jednej** funkcji (`core/hub/client.py`), `propagate_attrs()` **nigdy nie wywołane**, zero scores/datasets/experiments |
| **Rejestr narzędzi / `@tool` ze schematem z sygnatury** | 3 zadania S03 to pętle narzędziowe | ❌ brak — mamy **trzy ręcznie klepane** executory (s01e02, s01e03, s02e04), każdy z tym samym if/elif |
| **Embeddingi** | e04: NL („potrzebuję kabla 10 m") → pozycja w CSV; e01: klastrowanie podobnych notatek | ❌ brak w całej warstwie LLM. Tańsza alternatywa: `rapidfuzz` albo jedno tanie wywołanie LLM |
| **Prawdziwe bloki `tool_result`** | wierność protokołu, korelacja tool-call | ⚠️ typ `ToolResult` **istnieje, ale nieużywany** — wyniki wstrzykiwane jako udawane wiadomości `user` |
| **Koperta odpowiedzi narzędzia** (`next_action`/`recovery`/`diagnostics`) | wzorzec wprost z lekcji e04 — sterowanie agentem przez wynik narzędzia | ❌ brak |

### 🟢 FUN AND EDUCATIONAL

- **Promptfoo** — oś lekcji e01 i e04 (taksonomia asercji: deterministyczne / programistyczne /
  model-graded `llm-rubric`). Node CLI, więc używalny obok Pythona.
- **`pydantic-ai` — JUŻ ZAINSTALOWANE, NIGDY NIEUŻYTE.** `TestModel`/`FunctionModel` to
  gotowa ścieżka do deterministycznego testowania agentów — dokładnie ta luka, którą mamy.
- **`mcp[cli]` — zainstalowane, nieużyte.** MCP przewija się przez e02/e03/e05.
- **`mem0ai` — zainstalowane, nieużyte.** Odpowiednik „Observational Memory" z lekcji.
- **Anthropic native `code_execution`** (`core/llm/native_tool_code_execution.py`) —
  serwerowy sandbox z trwałym REPL-em; wprost odpowiada motywowi „code execution + sandbox"
  z e02. Minus: tylko Anthropic i poza ścieżką `LLMClient`.
- **Generative UI** z e05 (artifacts / json-render / MCP Apps) — najbardziej „zabawowa"
  część sezonu; nasz `webui/` z s02e02 to zalążek.
- **Narzędzia poznawcze `think` / `recall`** (e05) — sama ich obecność zmienia zachowanie modelu.

> 💡 **Osobne odkrycie z audytu:** w `pyproject.toml` jest **7 zależności zadeklarowanych i
> nigdy nieimportowanych**: `pydantic-ai` (+`-slim`, +`-harness`), `openai-agents`, `mcp`,
> `mem0ai`, `openapi-pydantic`, `prompt-toolkit`. Kilka z nich to dokładnie te „baterie",
> których chce S03 — już zapłacone, tylko niepodłączone. Decyzja (podłączyć albo usunąć) do
> podjęcia na sesji `pre-s03` — patrz `../season.md`.

### 🔧 WYMAGAJĄCE UPGRADU

| Obszar | Problem | Pilność |
|---|---|---|
| **Vision** | `LLMMessage.content` to goły `str` — multimodalność **strukturalnie niemożliwa** bez zmiany `types.py` + `base.py` + 4 adapterów | **Niska dla S03** — żadne z 5 zadań nie wymaga vision (`reactor_preview.html`/`savethem_preview.html` to podglądy dla człowieka, dane idą z API). Termin: najpóźniej S03→S04 |
| **Middleware omijany** | `.structured()` i `run_agent_loop()` wołają `self._provider` bezpośrednio → **rate-limit i cost-tracking nie działają** dla structured output i pętli agentowych | **Wysoka** — e01 to zadanie o koszcie, a nie mierzymy kosztu tam, gdzie go najwięcej |
| **Dynamiczne odkrywanie narzędzi** | `run_agent_loop(tools=[...])` bierze **statyczną** listę; e05 wymaga narzędzi odkrywanych w runtime przez `/api/toolsearch` | **Wysoka** (blokuje e05) |
| **Temperature / sampling** | zahardkodowane `0.0` na poziomie ABC, nieudostępnione przez fasadę; brak n-best, self-consistency, majority vote | **Średnia** — e05 to *cały* motyw „niedeterminizm jako przewaga" |
| **Warstwa async** | wszystkie providery synchroniczne → brak równoległych tool-calls | Średnia (wydajność, nie blokada) |
| **Brak jakiegokolwiek harnessu eval** | zero evals/datasetów/scoringu. `core/llm/classify.py` to jedyny prymityw sędziego; `data/run-history/` to jedyny surowy korpus | **Wysoka koncepcyjnie** — to teza całego sezonu |

## Tematy do ogarnięcia (w kolejności zwrotu z inwestycji)

1. **Model danych observability i ewaluacji** — hierarchia `Session → Trace → Span →
   Generation`; różnica *offline* (CI) vs *online* (produkcja) eval; anatomia evala
   (zadanie + dataset + score 0–1); taksonomia asercji (deterministyczna / programistyczna /
   model-graded). *Dlaczego:* to teza sezonu i wprost temat e01.
2. **Inżynieria kosztu LLM** — pięć dźwigni: tokeny wejściowe, **cache**, tokeny
   wyjściowe (w tym liczba kroków agenta), liczba zapytań (równoległość), rozmiar modelu.
   Plus asymetria cennika: **output kosztuje więcej niż input** → projektuj wyjście modelu tak,
   by było malutkie mimo dużego wejścia. *Dlaczego:* e01 jest punktowane dokładnie za to.
3. **Projektowanie narzędzi dla cudzego agenta** — wąski zakres zamiast pełnego API, opis jako
   artefakt krytyczny, koperta `next_action`/`recovery`/`diagnostics`, twarde limity rozmiaru
   odpowiedzi. *Dlaczego:* e04 ocenia dokładnie tę umiejętność.
4. **Algorytmy deterministyczne pod ograniczeniami** — BFS/DP nad przestrzenią stanów,
   planowanie przy ruchomych przeszkodach, optymalizacja dwuzasobowa. *Dlaczego:* e03 i e05 to
   klasyczne CS, nie LLM. Próba rozwiązania ich modelem to najdroższa możliwa droga.
5. **Feedback kontekstowy i pętla agenta** — pięć wyzwalaczy autonomii (wiadomości, hooki,
   webhooki, cron, heartbeat), hooki cyklu życia, błąd narzędzia zwracający *sugestię* zamiast
   samego błędu, limit rozmiaru wyniku → zapis do pliku zamiast do kontekstu. *Dlaczego:* e03,
   i wprost łata naszą największą słabość w `run_agent_loop`.
6. **Prompt injection i izolacja uprawnień** — system prompt traktuj jako publiczny; dostęp
   kontroluj **wyłącznie kodem, nigdy promptem**; osobny izolowany klasyfikator zwracający
   token weryfikowany w kodzie. *Dlaczego:* e02 explicite; e04 wystawia nasz endpoint światu.
7. **Dynamiczne odkrywanie narzędzi (RAG nad narzędziami)** — rejestr + wyszukiwanie
   semantyczne zamiast statycznej listy. *Dlaczego:* mechanika e05.
8. **Sandbox i wykonywanie kodu jako uniwersalny toolset** — filesystem + exec jako pamięć,
   kanał komunikacji i substrat obliczeniowy. *Dlaczego:* powtarza się w e02, e03, e05.

## Vision + embeddingi + modele lokalne — plan wdrożenia (gdy przyjdzie termin)

Dwa osobne kawałki, różny koszt:

1. **Adaptery (tanie).** OpenRouter, LM Studio, Ollama, llama.cpp wszystkie wystawiają
   API zgodne z OpenAI. Bloker: `base_url` zahardkodowany przez SDK. Etap 1 z
   `strategy/llm-selection.md` (wyciągnięcie `base_url` do konstruktora) odblokowuje
   wszystkie cztery naraz — godziny, nie dni.
2. **Multimodalność (drogie).** `LLMMessage.content: str` → lista bloków treści, dotyka
   `types.py` + `base.py` + wszystkie adaptery. Nie da się obejść lokalnymi modelami —
   to warstwa niżej niż wybór providera.

Trzeci powód za modelami lokalnymi (poza kosztem i doborem modeli specjalistycznych):
**modele komercyjne odmawiają na moderacji** — w komentarzach do s02e05 ludzie dostawali
od OpenAI `403 illicit/violent` za „zniszcz tamę". Model lokalny nie ma tego problemu.

Kontrargument z danych S03: modele lokalne wypadały **słabo w zadaniach agentowych**
(s03e05: „każdy lokalny model zawiódł"; s03e02: małe modele gubiły się po kilku
iteracjach), ale **dobrze w zadaniach wsadowych** (s03e01: `qwen3.5:9b` ~40 min, ale 100%
skuteczności). Polityka: **lokalne do percepcji i klasyfikacji wsadowej, chmurowe do
rozumowania w pętli.**

## `pydantic-ai` — rozwidlenie drogi, nie dołożenie zależności

Pokrywa się funkcjonalnie z `LLMClient`, czterema adapterami, `run_agent_loop()`,
`Tool`/`ToolCall`, `.structured()`. Przyjęcie go oznacza że spora część `core/llm/`
staje się martwa.

- **Ścieżka A — zostajemy przy własnym core.** Pełna kontrola, ale każdą brakującą
  rzecz (vision, embeddingi, async, streaming, rejestr narzędzi, prawdziwe `tool_result`)
  dopisujemy sami.
- **Ścieżka B — przechodzimy na `pydantic-ai`.** Vision, embeddingi, async, streaming,
  rejestr narzędzi, integracja z Logfire i `TestModel`/`FunctionModel` do evalsów z
  półki. Koszt: migracja wszystkich zadań + utrata części kontroli.

Rozstrzygnąć świadomie na sesji `pre-s03`, przed pisaniem kodu S03 — im później, tym
droższa migracja (każde kolejne zadanie dokłada kodu do przepisania).
