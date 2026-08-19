> **ZARCHIWIZOWANE 2026-08-18** — pozycje z tego dokumentu wyekstrahowane do Linear (team Aid4u).
> Mapowanie stare-ID → AID-XXX:
>
> | Stare ID | AID-XXX | Tytuł |
> |---|---|---|
> | Qodo-A1 (=R6) | [AID-15](https://linear.app/aid4u/issue/AID-15) | BaseTask.run() zawsze wysyła odpowiedź drugi raz |
> | Qodo-A2 | [AID-16](https://linear.app/aid4u/issue/AID-16) | WARSAW_TZ wywalane przy imporcie bez tzdata |
> | Qodo-A3 | [AID-17](https://linear.app/aid4u/issue/AID-17) | gemini_key_for_tier() nie waliduje 'tier' |
> | Qodo-A4 | [AID-18](https://linear.app/aid4u/issue/AID-18) | ToolCall.id w adapterze Gemini może się dublować |
> | Qodo-A5 | *(komentarz do [AID-11](https://linear.app/aid4u/issue/AID-11), nie nowy issue)* | Nazwy sekretów wychodzą do Logfire Cloud -- scalone z pre-istniejącym ticketem "fix/core-secrets.py logging" |
> | Qodo-A6 | [AID-19](https://linear.app/aid4u/issue/AID-19) | genai-prices w hot-path, niezadeklarowane w pyproject.toml |
> | Qodo-A7 | [AID-20](https://linear.app/aid4u/issue/AID-20) | SecretsManager.list() tworzy/niszczy ThreadPoolExecutor |
> | Qodo-A8 | [AID-21](https://linear.app/aid4u/issue/AID-21) | Martwe zdublowane przypisanie logfire_mod |
> | Qodo-B1 | [AID-22](https://linear.app/aid4u/issue/AID-22) | [ODŁOŻONE/learning-mode] GeoPoint.distance_to() truthiness vs is None |
> | Qodo-B2 | [AID-23](https://linear.app/aid4u/issue/AID-23) | [ODŁOŻONE/learning-mode] GeoPoint.is_nearest_to() kubełkowanie float |
> | Qodo-B3, B4 | *(nie migrowane)* | ✅ zrobione — naprawione przez autora 2026-08-15 |
> | Qodo-aneks-s01e02-tests | [AID-24](https://linear.app/aid4u/issue/AID-24) | [ODŁOŻONE/learning-mode] 2 pominięte testy + 2 martwe asercje |
> | Qodo-B5 | [AID-25](https://linear.app/aid4u/issue/AID-25) | s01e03_proxy: HubClient() na poziomie modułu wymaga APIKEY przy imporcie |
> | Qodo-B6 | [AID-26](https://linear.app/aid4u/issue/AID-26) | [ODŁOŻONE] s01e03_proxy: _sessions/history bez locka |
> | Qodo-B7 | [AID-27](https://linear.app/aid4u/issue/AID-27) | [ODŁOŻONE] s01e03_proxy: check_package/redirect_package raportują sukces mimo ok:false |
> | Qodo-B8 (=R7) | [AID-28](https://linear.app/aid4u/issue/AID-28) | s02e03_failure: except httpx.HTTPStatusError zbyt szeroki |
> | Qodo-B9 | [AID-32](https://linear.app/aid4u/issue/AID-32) | s02e03_failure: _LINE_RE wymaga dwucyfrowej godziny |
> | Qodo-B10 (=CodeRabbit-A) | [AID-30](https://linear.app/aid4u/issue/AID-30) | s02e03_failure: brak globalnego egzekwowania budżetu tokenów |
> | Qodo-B11 (=CodeRabbit-B) | [AID-31](https://linear.app/aid4u/issue/AID-31) | s02e03_failure: render_line() nie sanityzuje \n/\r |
> | Qodo-aneks-basedpyright | [AID-33](https://linear.app/aid4u/issue/AID-33) | pyproject.toml inlayHints array-of-tables |
> | Qodo-aneks (17 plików unittest.mock) | *(komentarz do [AID-14](https://linear.app/aid4u/issue/AID-14), nie nowy issue)* | scalone z pre-istniejącym ticketem "mixing pytest z unitest" |
> | Qodo-aneks-unclosed-clients | [AID-34](https://linear.app/aid4u/issue/AID-34) | Niezamykane httpx.Client()/TestClient(app) w testach |
> | Qodo-aneks-missing-agents-md | [AID-35](https://linear.app/aid4u/issue/AID-35) | Brak AGENTS.md w 4 katalogach |
> | Qodo-aneks-zero-coverage | [AID-36](https://linear.app/aid4u/issue/AID-36) | Zero pokrycia testami s01e04_sendit/s02e03_failure |
> | Qodo-aneks-fetch-spk | [AID-37](https://linear.app/aid4u/issue/AID-37) | fetch_spk_files.py: brak CSV daje cichy no-op |
> | Qodo-aneks-s01e03-flag-log | [AID-38](https://linear.app/aid4u/issue/AID-38) | s01e03_proxy: log flagi zawiera pełną treść wiadomości |
> | Qodo-aneks (test_gemini_integration .env fallback) | *(pokrywa się z pre-istniejącym [AID-5](https://linear.app/aid4u/issue/AID-5))* | get_secrets() nie ładuje .env → fałszywy skip |
> | Qodo-D-non-code-non-main | [AID-39](https://linear.app/aid4u/issue/AID-39) | [ODRZUCONE] reguła 'non-code files na non-main branch' |
> | Qodo-D-native-tools-direct | [AID-40](https://linear.app/aid4u/issue/AID-40) | [ODRZUCONE] native_tool_*.py woła Anthropic bezpośrednio |
> | Qodo-D-chat-handler | [AID-41](https://linear.app/aid4u/issue/AID-41) | [ODRZUCONE] '/chat handler usunięty' |
> | Qodo-D-flag-pattern-marker | [AID-42](https://linear.app/aid4u/issue/AID-42) | [ODRZUCONE] Brak markera FLAG_PATTERN_DETECTED |
> | .flags.json publiczne repo | *(nie migrowane)* | pytanie etyczne/regulaminowe, `strategy/open-decisions.md`, nie issue |
>
> **Krok 0 (decyzja o subskrypcji Qodo) rozstrzygnięty** — Qodo discontinued 2026-08-16, patrz
> root `AGENTS.md`.
>
> Pełne opisy żyją teraz wyłącznie w Linear — ten plik zostaje jako historyczny ślad triage'u.

# Triage nietkniętych uwag Qodo z zamkniętych PR-ów

**Data:** 2026-08-15 · **Zakres:** wszystkie 59 zamkniętych PR-ów (#1–#66) · **Bot:** `qodo-code-review`

## Metoda

Zrzut przez GraphQL (`comments`, `reviews`, `reviewThreads` z `isResolved`) dla każdego zamkniętego
PR-a. Znalezione: **129 wątków od Qodo, w tym 70 nierozwiązanych.** Każdy nierozwiązany wątek
sprawdzony wobec bieżącego stanu `main` (`7e4221a`) — poniżej są **wyłącznie te, które nadal żyją w
kodzie**. Wątki naprawione po drodze albo świadomie odrzucone są wypisane na końcu, żeby nie wracały
przy kolejnym przebiegu.

Filtr zgodnie z ustaleniem: **kontrakty i rzeczy dotykające więcej niż jednego zadania** w sekcjach A/B,
reszta jednym zdaniem w aneksie.

---

## ⚠️ Ustalenie meta: od PR#58 nie ma żadnego review Qodo

PR-y **#58–#66** (2026-08-09) mają od Qodo tylko komunikat rozliczeniowy:
*„Qodo reviews are paused because the subscription is no longer active"*. Zero wątków, zero sugestii.

Bez przeglądu przeszło m.in.:
- #64 — kill switch (grupy procesów, budżety runu),
- #65 — refactor `HubClient` (konsolidacja GET, walidacja treści),
- #66 — s02e05 drone.

To jest największa pojedyncza dziura w tym raporcie: dziewięć PR-ów, w tym dwa dotykające rdzenia,
nie zostało przejrzanych przez nic poza CodeRabbitem. **Decyzja do podjęcia przed sezonem 3:**
reaktywować subskrypcję, przełączyć się na inny mechanizm (np. `/code-review` lokalnie przed merge),
albo świadomie przyjąć, że od teraz review robi tylko CodeRabbit.

---

## A. Kontrakty rdzenia — rzutują na więcej niż jedno zadanie

### A1. `BaseTask.run()` zawsze wysyła odpowiedź drugi raz — kolizja z zadaniami iteracyjnymi
`core/tasks/base.py:119` · `tasks/s02e03_failure/solution.py:223` · PR#56 · **Action required**

`run()` bezwarunkowo woła `_submit()` po `solve()`. `FailureTask.solve()` prowadzi własną pętlę
`/verify` (własne `hub.submit()`), znajduje flagę i **zwraca sam `answer`, gubiąc flagę** — więc CLI
wysyła to samo jeszcze raz i zapisuje flagę z drugiej odpowiedzi. Jedno wywołanie huba w plecy i
zapisana flaga zależy od tego, czy hub powtarza flagę przy ponownym zgłoszeniu.

`FailureTask` nie nadpisuje `_submit()` — potwierdzone, problem żyje.

**Dlaczego cross-task:** `BaseTask` nie ma żadnego haka „solve już wysłał". Każde kolejne zadanie
z iteracyjnym `/verify` (a sezon 3 takie będzie miał) wpadnie w dokładnie to samo. To jest luka
w kontrakcie bazowym, nie bug jednego zadania.

**Mechanizm poprawki:** dodać do `BaseTask` jawny kontrakt — np. pole `self._solved_flag`, a
`_submit()` zwraca je bez wywołania huba, jeśli jest ustawione. Alternatywa (gorsza): override
`_submit()` w `FailureTask`, co zostawia pułapkę dla następnego zadania.
**Blast radius:** wszystkie zadania — zmiana w klasie bazowej. Wymaga testu na `BaseTask`.
**Kompromis:** rozszerza kontrakt `BaseTask` o stan, którego dziś nie ma; alternatywą jest zostawienie
tego jako znanej pułapki i dokumentowanie w `core/AGENTS.md`.

### A2. `WARSAW_TZ` wywalane przy imporcie — bez tzdata nie startuje żadne zadanie
`core/config.py:29` · PR#39 · **Action required**

```python
WARSAW_TZ = zoneinfo.ZoneInfo("Europe/Warsaw")   # na poziomie modułu
```

`core/tasks/base.py` importuje to i używa w `_save_output()`. W środowisku bez bazy IANA (slim
kontener, część obrazów VPS) `ZoneInfoNotFoundError` leci **przy imporcie**, więc pada wszystko —
łącznie z kolekcją pytest.

**Dlaczego cross-task:** ścieżka importu wspólna dla każdego zadania. Deploy na VPS (`deploy/`) jest
dokładnie tym scenariuszem, w którym to wybucha.
**Mechanizm:** leniwe `get_warsaw_tz()` z `@cache`, albo `try/except ZoneInfoNotFoundError` z fallbackiem
na `timezone.utc`. Jeśli tzdata ma być twardym wymogiem — dodać `tzdata` do zależności i zostawić
głośny błąd, ale świadomie.
**Kompromis:** fallback na UTC cicho zmienia nazwy plików wyjściowych (znaczniki czasu) zamiast
wywalić się głośno. Wybór: cichy fallback vs. jawna zależność.

### A3. `gemini_key_for_tier()` nie waliduje `tier` — literówka = cichy zły klucz
`core/config.py:95-97` · PR#8 · **Review recommended**

```python
return self.gemini_key_premium if tier == "premium" else self.gemini_key
```

Docstring obiecuje `'standard' | 'premium'`, kod traktuje **wszystko poza dokładnym `"premium"`** jako
standard. `"Premium"`, `"premuim"`, `None` → cicho klucz standardowy, czyli inny projekt, inna quota,
inny rachunek. Albo mylący błąd „brak klucza".

**Dlaczego cross-task:** `create_provider(..., tier=...)` przepuszcza dowolny string od wołającego,
a to wejście do całej warstwy LLM.
**Mechanizm:** normalizacja (`(tier or "standard").lower()`) + `raise ValueError` dla nieznanej wartości
+ test na granicy `create_provider()`.
**Blast radius:** mały i lokalny; ryzyko tylko takie, że coś dziś przekazuje śmieciowy tier i zacznie
się wywalać — co jest pointą.

### A4. `ToolCall.id` w Gemini może się dublować — łamie kontrakt trzymany przez inne adaptery
`core/llm/adapters/gemini.py:185-186` · PR#19 · **Review recommended**

```python
id=part.function_call.id or part.function_call.name,
```

Gdy SDK nie poda `id`, a model wywoła to samo narzędzie dwa razy w jednej odpowiedzi, oba wywołania
dostają identyczne `id`. Adaptery Anthropic i OpenAI zawsze mają unikalne id — czyli niejawny kontrakt
„`id` jednoznacznie identyfikuje wywołanie" jest łamany tylko przez Gemini.

**Dlaczego cross-task:** dotyczy każdej pętli agentowej na Gemini. Wzorzec `run_agent_loop` jest już
używany przez s01e02 i s02e04 i będzie podstawą sezonu 3.
**Mechanizm:** licznik po częściach odpowiedzi — `f"{name}:{idx}"` — zamiast gołej nazwy.
**Kompromis:** żaden realny; to trzylinijkowa zmiana.

### A5. Nazwy sekretów wychodzą do Logfire Cloud
`core/secrets.py:132,138,140` · PR#10 · **Review recommended**

`logfire.info(f"Stored {key} in keyring")` / `f"Deleted {key} from keyring"` /
`f"Key not found in keyring: {key}"`. Wartości nie wyciekają, ale **inwentarz sekretów i moment
rotacji już tak** — a przy skonfigurowanym `LOGFIRE_TOKEN` idzie to poza host.

**Dlaczego cross-task:** to cała warstwa sekretów, wspólna dla wszystkiego.
**Mechanizm:** stały komunikat bez `key`, albo `key` jako pole strukturalne objęte polityką redakcji.
**Kompromis:** tracisz możliwość wyklikania w Logfire „który sekret ostatnio ruszałem" — realnie mała
strata przy garstce kluczy.

### A6. `genai_prices` importowane w hot-path, ale niezadeklarowane w `pyproject.toml`
`core/llm/middleware.py:98` · `pyproject.toml` · PR#13 · **Review recommended**

Pakiet jest zainstalowany, ale **wchodzi tranzytywnie** (przez Logfire) — w `pyproject.toml` nie ma go
w zależnościach. Dziś działa. Gdy Logfire przestanie go ciągnąć, `CostTrackMiddleware` zacznie łapać
`ModuleNotFoundError` i logować `logfire.warning` **przy każdym wywołaniu LLM**, plus koszt nieudanego
importu w każdej iteracji pętli agentowej.

**Dlaczego cross-task:** `LLMClient` zawsze wpina `CostTrackMiddleware` w łańcuch.
**Mechanizm:** dopisać `genai-prices` do zależności (jeśli cost tracking ma działać zawsze), albo
zcache'ować wynik importu w `__init__` i po pierwszym `ModuleNotFoundError` wyłączyć tracking na stałe.
**Kompromis:** jawna zależność = jeden pakiet więcej do pilnowania; leniwe wyłączanie = cichsze, ale
łatwiej przegapić, że koszty przestały się liczyć.
*(Brak tracebacku z tego samego wątku jest już naprawiony — `exc_info=True`.)*

### A7. `SecretsManager.list()` tworzy i niszczy pulę wątków przy każdym wywołaniu
`core/secrets.py:153` · PR#18 · **Optional**

`ThreadPoolExecutor()` bez `max_workers`, bez guardu na pustą listę, budowany per wywołanie. `info()`
woła `list()`. Przy domyślnej liczbie kluczy narzut potrafi zjeść zysk z równoległości.
**Mechanizm:** `max_workers=min(8, len(keys_list))`, wczesny return `{}` dla pustej listy.
**Kompromis:** niski priorytet — to nie jest ścieżka gorąca, poprawka jest kosmetyczna wobec reszty listy.

### A8. Martwy duplikat przypisania w `ServerFactory.create`
`core/server/factory.py:49,51` · PR#37 · **Optional**

```python
logfire_mod = logfire

logfire_mod = logfire
```
Dwie identyczne linie pod rząd. Zero wpływu na działanie, ale to jedyny ślad po naprawie z PR#16
(która sama jest już zrobiona poprawnie — przypisanie jest przed `instrument_fastapi`).

---

## B. Kontrakty pojedynczych zadań — realne bugi, nadal w kodzie

Sezony 1 i 2 są zamknięte, flagi zdobyte. Wartość tych poprawek jest **wyłącznie jako higiena kodu,
który wjedzie do sezonu 3** (proxy, pętla verify). Przy aktywnym EFFICIENCY MODE część z nich
jest świadomie do zostawienia — zaznaczam które.

> **`s01e02` wypada z tego planu w całości — decyzja z 2026-08-15.** B1 i B2 są zapisane jako
> świadomie odłożone w `tasks/s01e02_findhim/AGENTS.md` (sekcja Local Contracts), razem z pełnym
> uzasadnieniem i oceną osiągalności. Skrót: zadanie zaliczone, `GeoPoint` nie jest importowany
> poza własnym zadaniem, w `tasks/s03/requirements/` nie ma geodezji, a oba defekty powstały
> w learning mode i ręcznie — ich naprawa jest materiałem do nauki, zarezerwowanym na powrót
> do learning mode po 20 flagach. B3 i B4 autor naprawił samodzielnie tego samego dnia.

| # | Miejsce | Problem | Warto? |
|---|---------|---------|--------|
| B1 | `tasks/s01e02_findhim/solution.py:39` | `distance_to()` miesza truthiness z `is None`: `is not` wiąże mocniej niż `and`, więc sprawdzenie na `None` dotyczy tylko `target.longitude`, a pozostałe trzy współrzędne odrzucają poprawne `0.0` fałszywym `ValueError`. Zgłoszone dwa razy (PR#33, PR#39). | Odłożone → `s01e02/AGENTS.md`; nieosiągalne dla danych PL |
| B2 | `tasks/s01e02_findhim/solution.py:74-79` | `is_nearest_to()` kubełkuje kandydatów po dokładnej wartości `float` jako kluczu dicta. Kontrakt („wszystkie najbliższe") vs. implementacja. | Odłożone → `s01e02/AGENTS.md`; praktycznie nieosiągalne przy 6 miejscach po przecinku |
| ~~B3~~ | `tasks/s01e02_findhim/solution.py:317` | `parse_location_history()` cicho zwracało `[]` dla błędnego typu. | ✅ naprawione 2026-08-15 |
| ~~B4~~ | `tasks/s01e02_findhim/solution.py:6` | `from _collections_abc import Iterator` — prywatny moduł CPythona. | ✅ naprawione 2026-08-15 |
| B5 | `tasks/s01e03_proxy/server.py:63` | `_hub = HubClient()` na poziomie modułu → `HubClient.__init__` żąda `APIKEY` już przy imporcie. Import modułu (a więc i kolekcja pytest) pada w środowisku bez sekretów. | **Tak** — blokuje CI/świeży klon |
| B6 | `tasks/s01e03_proxy/server.py:62,77-85` | `_sessions` (OrderedDict) i listy `history` mutowane bez locka, a endpoint jest synchroniczny → Starlette puszcza go w threadpoolu. Równoległe requesty mogą przeplatać LRU i edycje historii. | Tylko jeśli proxy wraca w s03 |
| B7 | `tasks/s01e03_proxy/tools.py:96,117` | `check_package`/`redirect_package` formatują komunikat sukcesu nie patrząc na payload huba (`ok: false`). LLM dostaje „przekierowana" także przy błędzie aplikacyjnym. | Tylko jeśli proxy wraca |
| B8 | `tasks/s02e03_failure/solution.py:270-271` | `except httpx.HTTPStatusError: return exc.response.json()` łapie **wszystko** ≥400. 401/403/500 udaje feedback z `/verify`, a nie-JSON body wywala się na parsowaniu zamiast pokazać prawdziwy błąd. | **Tak** — wzorzec pętli verify wróci |
| B9 | `tasks/s02e03_failure/solution.py:38` | `_LINE_RE` wymaga `HH:MM:SS` z dwucyfrową godziną; dokumentacja zadania dopuszcza `H:MM`/`HH:MM` → linie logu cicho wypadają z przetwarzania. | **Tak** — cicha utrata danych |
| B10 | `tasks/s02e03_failure/solution.py:182-192` | `_hard_trim()` nie tyka wpisów `pinned` i przy samych pinned zwraca bez zmian. Jeśli pinned same przekroczą budżet, nie ma mechanizmu zejścia → wyczerpanie `_MAX_VERIFY_ATTEMPTS`. | Opcjonalnie |
| B11 | `tasks/s02e03_failure/solution.py:109-111` | `render_line()` nie sanityzuje `\n`/`\r` w `desc` pochodzącym z LLM → kontrakt „jedno zdarzenie na linię" może pęknąć. | Opcjonalnie |

---

## C. Aneks — reszta nierozwiązanych wątków, po jednym zdaniu

- **`pyproject.toml:101`** — `[[tool.basedpyright.python.analysis.inlayHints]]` to array-of-tables zamiast
  zwykłej tabeli, więc basedpyright może całkiem ignorować te ustawienia (PR#33). **Skorygowane
  2026-08-15:** pierwsza wersja dokumentu podbijała to ponad resztę aneksu, zakładając, że stąd biorą
  się ubogie inlay hints — błędne założenie. Statyczną analizą typów zajmuje się **wyłącznie `pyrefly`**;
  `basedpyright` to fallback bez obecnego znaczenia. Zostaje jako trzydziestosekundowa poprawka
  higieniczna, nie jako priorytet.
- **17 plików testowych importuje `unittest.mock`** mimo `pytest-mock>=3.14` w zależnościach; Qodo
  zgłosił to pięć razy (PR#8, #11, #12, #15, #19). `tests/AGENTS.md` mówi tylko „Use pytest", nie zakazuje
  `unittest` — to decyzja, nie bug.
- **Niezamykane klienty w testach** — `httpx.Client()` w `tests/core/test_hub.py:57,194,307,442` i
  `TestClient(app)` w `tests/core/server/test_factory.py:12,24,45` bez `close()`/context managera (PR#11, #20, #37).
- **Dwa pominięte testy** — `tasks/s01e02_findhim/test_solution.py:96,178` (`@pytest.mark.skip`, PR#33, #39).
- **Brak `AGENTS.md`** w `tasks/common/`, `core/llm/`, `data/input/s01e04_sendit/`, `tasks/s01e01_people/`
  (PR#13, #33, #45, #49) — realny dług DOX, bo `core/llm/` i `tasks/common/` to trwałe granice.
- **Brak testów** dla `tasks/s01e04_sendit/` i `tasks/s02e03_failure/`; `tasks/s02e02_electricity/`
  nadal bez `solution.py` (PR#51, #52, #53).
- **`data/input/s01e04_sendit/fetch_spk_files.py:42`** — brak `SPK_files_list.csv` daje cichy no-op
  zamiast błędu (PR#49).
- **`tests/core/test_gemini_integration.py`** — `get_secrets()` nie ładuje `.env`, więc klucz ustawiony
  tylko w `.env` daje fałszywy skip (PR#6).
- **`tasks/s01e03_proxy/server.py:108`** — log wykrycia flagi zawiera pełny `msg`, czyli samą flagę,
  w telemetrii.

---

## D. Zamknięte — nie wracać do tego przy kolejnym przebiegu

> **Sprostowanie ramy tego rozdziału (2026-08-15).** Pierwsza wersja tego dokumentu opisywała
> powtarzalne znaleziska Qodo tak, jakby każde z nich zostało rozważone i odrzucone. To nieprawda
> i warto to mieć zapisane, bo prowadzi do złych wniosków przy kolejnym przebiegu.
>
> Świadomą decyzją są **wyłącznie dwie pozycje niżej, obie z zapisanym uzasadnieniem** w AGENTS.md
> (non-code na non-main branch; native tools wołające Anthropic bezpośrednio). **Cała reszta** —
> `unittest.mock` zgłoszony pięć razy, brakujące `AGENTS.md` cztery razy, niezamykane klienty trzy
> razy, pominięte testy dwa razy — została bez naprawy **z pośpiechu i z nieznajomości narzędzia**:
> Qodo *sygnalizuje* problemy i nie rozwiązuje ich sam, a to nie było jasne w trakcie pracy.
> To jest przykład nieznajomości własnego stacku, nie triage'u. Powtarzalność znaleziska nie jest
> dowodem, że zostało odrzucone — jest dowodem, że nikt go nie zamknął.
>
> Praktyczny wniosek na przyszłość: znalezisko powtórzone na trzecim PR-ze albo naprawiamy, albo
> **jawnie zapisujemy odrzucenie w odpowiednim AGENTS.md**. Trzecia opcja (przewijamy dalej) jest
> tym, co wyprodukowało ten dokument.

**Naprawione po drodze** (wątek nadal formalnie „unresolved" na GitHubie, ale kod jest już dobry):
- `HubClient` retry na trwałych 4xx (PR#49) → naprawione w #65, `_is_retryable_http_error`.
- Path traversal w `fetch_spk_files.py` (PR#49) → naprawione, `_safe_rel_path()` (#60/#62).
- `CostTrackMiddleware` gubi traceback (PR#13) → `exc_info=True`.
- `logfire_mod` gubione przy błędzie instrumentacji (PR#16) → przypisanie przed `instrument_fastapi`.
- Brak `solution.py` w folderach s02 (PR#52) → nadrobione wszędzie poza `s02e02_electricity`.
- Docstring `native_tool_bash.py` wskazujący na nieistniejący plik (PR#43) → plik już istnieje.

**Świadomie odrzucone — decyzje projektu, nie do relitygowania:**
- **„Non-code files na non-main branch"** (PR#12, #13, #21, #46, #51, #52, #53) — reguła Qodo 2059936,
  już rozpatrzona i odrzucona, zapisane w `AGENTS.md:180`.
- **„`native_tool_*.py` woła Anthropic bezpośrednio"** (PR#41, #42, #43, #44) oraz **„adapter Gemini
  konfiguruje `google.genai` poza `client.py`"** (PR#7, #19) — świadoma decyzja architektoniczna,
  udokumentowana w `core/AGENTS.md:96-103` (batch workflow: każdy native tool to plik net-new,
  gałęzie nie kolidują niezależnie od kolejności merge). Qodo będzie to zgłaszać dalej — ignorować.
- **„`/chat` handler usunięty"** (PR#48) — endpoint świadomie zmieniony na `POST /` pod wymagania huba.
- **„Brak markera `FLAG_PATTERN_DETECTED`"** (PR#47) — jest stały string `"Flag detected in incoming
  message"` + `session_id`; wymóg spełniony inną nazwą.

**Do osobnej decyzji, nie do poprawki:**
- **`.flags.json` jest w gitcie, a repo jest PUBLICZNE.** Qodo zgłosił to jako „secret committed"
  (PR#39) — jako *credential* to fałszywy alarm, bo flagi to rejestr postępu kursu. Ale publiczne repo
  z flagami AI_Devs to spoiler dla innych kursantów. To pytanie o etykę/regulamin kursu, nie o bezpieczeństwo.

---

## Plan wdrożenia

Routing commitów zgodnie z `AGENTS.md:179` — kod (`.py`) przez branch + PR, non-code (`.md`, `.toml`)
prosto na `main`.

### Krok 0 — decyzja o review (przed czymkolwiek innym, ~0 kodu)
Rozstrzygnąć sprawę Qodo: reaktywacja / rezygnacja / zamiennik. Bez tego każdy PR z tego planu też
przejdzie bez przeglądu, co jest dokładnie tym problemem, który ten raport opisuje.

### Krok 1 — `main`, bez PR (~5 min)
- Naprawa `[[tool.basedpyright...inlayHints]]` → `[tool.basedpyright...inlayHints]` w `pyproject.toml`.
- Weryfikacja: otworzyć dowolny plik w edytorze i sprawdzić, czy inlay hints faktycznie się pojawiły.

### Krok 2 — PR `fix(core): contract hardening` (~1–1,5 h)
Jedna gałąź, jeden spójny temat: kontrakty rdzenia. Pozycje **A2, A3, A4, A5, A6, A8**.
- Każda pozycja + test na tej samej gałęzi.
- Test na A3 (nieznany tier) i A4 (dwa wywołania tego samego narzędzia) to jedyne, które wymagają
  pomyślunku; reszta jest mechaniczna.
- **DOX:** `core/AGENTS.md` do aktualizacji (zmiana kontraktu `gemini_key_for_tier`, zachowanie
  `WARSAW_TZ`, deklaracja `genai-prices`) — doc jedzie w tym samym PR, bo opisuje jego własny kod.
- Weryfikacja: `uv run pytest tests/core/`.

### Krok 3 — PR `fix(core): single submit contract for iterative tasks` (~1 h)
Osobno, bo **A1** zmienia klasę bazową i dotyka istniejącego zadania.
- Rozszerzenie `BaseTask` o jawną ścieżkę „solve już wysłał" + `FailureTask` korzystający z niej.
- Test na `BaseTask`: zadanie, które wysłało samo, nie wywołuje huba drugi raz.
- **DOX:** `core/AGENTS.md` (kontrakt `run()`/`_submit()`) oraz `tasks/s02e03_failure/AGENTS.md`.
- Weryfikacja: `uv run pytest tests/core/tasks/` + suchy bieg `s02e03` w trybie `dry_run`.

### Krok 4 — PR `fix(tasks): verify-loop correctness` (~30 min)
Wąski wybór z sekcji B — tylko to, co wróci w sezonie 3: **B8, B9** (`s02e03`, pętla `/verify`).
Uzasadnienie: protokół huba wraca w każdym sezonie, geodezja nie.
- B8: zawęzić `except httpx.HTTPStatusError` do statusu 400, resztę przepuścić dalej.
- B9: rozluźnić `_LINE_RE` do formatów dopuszczonych przez treść zadania.
- **`s01e02` (B1, B2) nie wchodzi** — odłożone do learning mode, patrz ramka w sekcji B
  i `tasks/s01e02_findhim/AGENTS.md`.
- **Świadomie pomijane:** B6, B7, B10, B11 — sezony zamknięte, EFFICIENCY MODE. Do odblokowania
  tylko jeśli proxy albo kompresja logów wracają w s03.

### Krok 5 — PR `fix(tasks): import-time secrets requirement in proxy server` (~20 min)
**B5** osobno, bo to jedyna rzecz z sekcji B, która psuje coś *teraz*: świeży klon bez `APIKEY` nie
zbierze testów. Wzorzec `_get_hub()` analogiczny do istniejącego `_get_llm()`.

### Krok 6 — dług DOX, na `main` bez PR (~30 min)
Brakujące `AGENTS.md`: `core/llm/`, `tasks/common/`, `data/input/s01e04_sendit/`, `tasks/s01e01_people/`
+ wpisy w indeksach DOX rodziców. To czyste non-code, więc prosto na `main`.

### Krok 7 — decyzje bez kodu (do rozstrzygnięcia, nie do zrobienia)
1. `unittest.mock` w 17 plikach testowych — migrować na `mocker`, czy dopisać w `tests/AGENTS.md`,
   że dopuszczamy? Migracja to ~2 h mechanicznej roboty bez zysku funkcjonalnego.
2. `.flags.json` w publicznym repo — zostawić, przenieść do prywatnego, czy zaciemnić?
3. Dwa `@pytest.mark.skip` w `s01e02` — dokończyć czy usunąć testy.
4. Zerowe pokrycie testami `s01e04_sendit` i `s02e03_failure` — akceptowane w EFFICIENCY MODE, ale
   warto to zapisać jawnie zamiast zostawiać jako przemilczenie.

### Czego ten plan nie robi
Nie tyka niczego z sekcji D. Nie migruje testów z `unittest.mock`. Nie centralizuje wywołań
`native_tool_*` przez `client.py` — to jest udokumentowana decyzja, nie dług.
