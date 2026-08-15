# Decyzja: na czym budujemy S03 i dalej — własny `core/llm/` vs `pydantic-ai`

**Sesja:** `pre-s03` · **Data:** 2026-08-15 · **Status:** rekomendacja do akceptacji autora
(przed pisaniem kodu S03) · **Źródła rozstrzygane:** `season.md` (linie 77-87),
`source/tool-inventory.md` (sekcja „rozwidlenie drogi", 130-144).

---

## Rekomendacja

**Ścieżka A — zostajemy przy własnym `core/`.** Wprowadzamy poprawki kontraktowe z
`closed-prs-qodo-triage.md` (te, które przeżywają — patrz niżej) i lecimy z S03 od `s03e03`.
`pydantic-ai` **nie wchodzi jako framework runtime**. Wchodzi co najwyżej `pydantic-evals` jako
**izolowane narzędzie pomiaru w e01** (opcjonalnie, patrz §6) — to nie jest drugi stack LLM, bo
nie dotyka `LLMClient` ani ścieżki `solve()→submit()`.

**Odrzucone:** B1 (nowe repo) i B2 (nadbudówka w tym repo). B1 najmocniej — to najdroższy wariant
pod EFFICIENCY MODE, a autorska „lekka preferencja" dla niego nie wytrzymuje policzenia kosztu (§9).

Jedno zdanie uzasadnienia: **z pięciu zadań S03 tylko jedno (e02) jest jednoznacznie pętlą
agentową, w której `pydantic-ai` cokolwiek wnosi — a najbardziej wartościowe osłony tego zadania
i tak trzeba napisać ręcznie w obu ścieżkach.** Migracja całej warstwy dla 1/5 zadań, w trybie
którego jedynym priorytetem jest tempo do 20 flag, to ujemny zwrot.

---

## 1. Pokrycie funkcjonalne — mierzone

`core/` to **3186 LOC** (zweryfikowane: `find core -name '*.py' | xargs wc -l`). Podział istotny
dla decyzji:

| Blok | Pliki | LOC | Status przy B |
|---|---|---:|---|
| **Rdzeń LLM pokrywający się z `pydantic-ai`** | `client.py` 151, `middleware.py` 166, `factory.py` 73, `types.py` 67, `base.py` 69, `classify.py` 63, `adapters/` (anthropic 125, gemini 203, openai 107, openrouter 19) | **1043** | martwy — zastąpiony przez `Agent`/`Model`/`RunUsage`/`FunctionToolset` |
| **Native tools (Anthropic server-side)** | `native_tool_bash` 195, `native_tool_text_editor` 234, `native_tool_code_execution` 118, `native_tool_web_search` 104 | **651** | **NIE** martwy — to serwerowe narzędzia Anthropica, już dziś **poza** `LLMClient`; `pydantic-ai` nie ma ich 1:1 |
| **Testy rdzenia LLM** | `tests/core/llm/**` | **~1471** | do przepisania pod nowy stack |

Czyli B kasuje **1043 LOC kodu + ~1471 LOC testów** i **wymaga przepisania** tego, co dziś działa.
Native tools (651 LOC) zostają tak czy siak — są ortogonalne do tej decyzji.

**Miejsca wywołań** (`grep` po `tasks/` + `run.py`, bez testów):

- Import `core.llm`: **8 plików**. Z tego **6 to s01/s02** (`s01e01`, `s01e02`, `s01e03`, `s02e03`,
  `s02e04`) — zadania **zamknięte, kod archiwalny, nie migrujemy** (ustalenie autora, przyjęte jako
  dane). Realnie w przód niosą tylko: `run.py:_make_llm()` (fabryka `LLMClient`) i **nowe `solve()`
  S03, których jeszcze nie ma**.
- `run_agent_loop()`: 3 call-sites — `s01e02`, `s01e03`, `s02e04`. **Wszystkie zamknięte.**
- `.structured()`: `s01e01`, `s02e03` (zamknięte) + `classify.py`.
- `classify()`: `s01e03` (zamknięte).

**Wniosek §1:** liczony „od dziś w przód" (§ poprawka autora) koszt migracji nie dotyczy żadnego
istniejącego call-site — wszystkie żywe wywołania są w zamkniętych sezonach. Migracja B to koszt
**przepisania rdzenia + testów**, żeby nowe `solve()` S03 pisać na frameworku zamiast na `LLMClient`.
To znaczy: płacisz pełną cenę migracji, a „oszczędzasz" tylko na kodzie, którego jeszcze nie napisałeś.

---

## 2. Czego S03 wymaga, a czego core dziś nie ma — cztery luki z `tool-inventory.md`

Dla każdej: czy `pydantic-ai` daje to z półki, czy i tak trzeba dopisać.

| Luka | `pydantic-ai` z półki? | Werdykt |
|---|---|---|
| **Middleware omijany przez `.structured()`/`run_agent_loop()`** — cost-tracking nie działa w e01 (zadaniu *o koszcie*). Dowód: `client.py:62` puszcza `self._chain` tylko w `complete()`; `client.py:73` i `client.py:117` wołają `self._provider.*` **bezpośrednio**. | **Tak** — `RunUsage.cost`/`input_tokens`/`output_tokens` liczone automatycznie na każdym `run()`, plus `logfire.instrument_pydantic_ai()`. | **Naprawialne w core taniej niż migracja.** To przepięcie dwóch metod przez istniejący `self._chain` — kilkadziesiąt linii, nie nowy framework. A e01 jest **batchem 10 000 plików**, nie pętlą agenta — koszt liczy się tam sumą po wywołaniach klasyfikatora, nie przez `UsageLimits` per-run. |
| **Dynamiczne odkrywanie narzędzi w runtime** (blokuje elegancki e05 — `/api/toolsearch`). Dziś `run_agent_loop(tools=[...])` bierze statyczną listę. | **Tak, realnie** — `FunctionToolset.add_function()` w trakcie runu, `ExternalToolset`, `DeferredLoadingToolset` (potwierdzone w docs 2.18). To jedyna luka, gdzie framework ma przewagę „z pudełka". | **Przewaga B — ale e05 da się deterministycznie.** Treść zadania: toolsearch zwraca 3 najlepsze wpisy (mapa, zasady ruchu, parametry pojazdów); to zbierasz raz i puszczasz **BFS/DP nad `(pozycja, paliwo, jedzenie)`**. Społeczność (`community-intel`): „każdy lokalny model zawiódł" w podejściu agentowym — sygnał, że e05 **nie chce** być pętlą agenta. Dynamiczny toolset rozwiązuje problem, którego przy dobrym podejściu nie masz. |
| **Propagacja błędów narzędzia do modelu** (e02 wymaga, by agent widział ban/rate-limit/503). Dowód: `client.py:137-139` łapie `except Exception` i wstawia stały `"ERROR: Tool execution failed."` — model nie dostaje kodu. | Framework przekazuje wyjątek/`ToolReturn` do modelu poprawnie. | **Naprawialne w core 3-liniową zmianą.** Przestać połykać w stały string, oddać `repr(exc)`/status. Obejście ręczne istnieje już w `s02e04`. Nie jest to powód do migracji. |
| **Twardy limit wyniku + rate limiter wychodzący + blacklist ścieżek w KODZIE** (e02: każda strata $4-10 stąd). | **NIE.** To logika domenowa narzędzia (truncacja `cat cooler.bin`, okno 30 req/min z 429-przedłużeniem, zakaz `/etc` `/root` `/proc` + `.gitignore`). Framework agentowy tego nie dostarcza — staff kursu **explicite błogosławi hardcode w kodzie narzędzia**. | **Piszesz sam w OBU ścieżkach.** To jest sedno e02 — i framework tu nie pomaga ani trochę. `truncate_tool_result()` już jest (`feat/killswitch`); rate limiter i blacklist trzeba dopisać niezależnie od A/B. |

**Wniosek §2:** z czterech luk trzy są tańsze do zamknięcia łatką w `core/` niż migracją; czwarta
(osłony e02) jest niezależna od stacku. Jedyna realna przewaga frameworka (dynamiczny toolset)
dotyczy zadania, które lepiej zrobić bez agenta.

---

## 3. Co jest niemigrowalne — koszt B1 (nowe repo)

Infrastruktura niezależna od decyzji LLM, którą przy **B1 trzeba przenieść ręcznie**:

| Blok | LOC | Uwaga |
|---|---:|---|
| `hub/` (`client.py` 258 + `cache.py` 75) | **333** | protokół `hub.ag3nts.org` — **nic tego nie zastąpi**, rdzeń każdego zadania |
| `secrets.py` | 169 | keyring, tiery kluczy |
| `config.py` | 135 | `WARSAW_TZ`, tiery Gemini |
| `observability/` (`decorators` 165 + `setup` 111) | 276 | Langfuse/Logfire bootstrap |
| `runtime/killswitch.py` | 163 | grupy procesów, budżety runu (`feat/killswitch`) |
| `net.py` | 77 | |
| `server/factory.py` | 94 | **potrzebny wprost dla e04** (publiczny endpoint) |
| **Razem** | **~1247** | |

Do tego **~11 plików `AGENTS.md`** w `aid4u/` (drzewo DOX), `deploy/` (systemd, ngrok, VPS),
`pyproject.toml`, `run.py` (CLI + registry `@task`). B1 znaczy: przenieść ~1247 LOC infry + całe
drzewo DOX + deploy + CLI, zanim napiszesz pierwszą linię `solve()` S03. **To jest praca o zerowej
wartości flagowej** — przepisujesz działające, żeby stało w innym katalogu.

B2 (to samo repo) tego kosztu nie ma — infra zostaje na miejscu. Ale B2 ma inny (§9).

---

## 4. Koszt mierzony czasem do pierwszej flagi S03E01

Rekomendowana kolejność ataku (z `season.md`): **e03 → e01 → e04 → e05 → e02**. Pierwsza flaga
sezonu to **e03 (reactor) — czysty algorytm BFS, zero LLM, framework kompletnie nieistotny.** Druga
to **e01 — batch, wzorzec z `s02e03` przenosi się prawie 1:1**.

- **Ścieżka A:** pierwsza flaga (e03) **dziś/jutro** — piszesz BFS, `run.py solve` już działa.
  Zero pracy stackowej na drodze.
- **Ścieżka B (dowolny wariant):** zanim `run.py solve s03e03` w ogóle wystartuje na nowym stacku,
  trzeba: przepisać fabrykę/adaptery/klienta, przepiąć `@task`/`BaseTask` (dziś `Template Method`
  na własnym `LLMClient`), zmigrować testy. **Kilka dni na coś, co e03 i tak nie użyje** (algorytm
  nie woła LLM). B opóźnia pierwsze **dwie** flagi sezonu (e03, e01) bez żadnego zysku dla nich —
  bo to nie są zadania agentowe.

**Kiedy B by się odrobiło?** Najwcześniej przy **e02** (5. w kolejce) i marginalnie e05 (4.). Czyli
zysk z migracji materializuje się **na końcu S03**, a koszt płacisz **na początku**. Pod EFFICIENCY
MODE (priorytet: dojść do 20 flag; brakuje S03+S04) to odwrotność tego, czego chcemy. Migracja
odrabia się **dopiero w S04** — jeśli w ogóle, bo tematyka S04 nieznana.

---

## 5. Escape hatch — ryzyko zablokowania się w połowie sezonu

Kurs regularnie łamie założenia frameworka:

- **e04 to nie jest zadanie agentowe po naszej stronie w ogóle** — *my budujemy 1-2 endpointy HTTP,
  ICH agent je woła* (treść: „Agent wysyła POST `{params: ...}` → oczekuje `{output: ...}`",
  odpowiedź 4-500 B). Framework agentowy `pydantic-ai` **nie dotyka tego zadania** — potrzebny jest
  hosting (`server/factory.py` + ngrok, udowodnione w s01e03) i ewentualnie fuzzy/embedding NL→CSV.
  To argument, że framework agentowy pokrywa **mniej** S03, niż się wydaje.
- **Własny protokół huba, wymuszony format odpowiedzi, żywa rozmowa przez proxy** (s01e03): przy
  własnym core zejście „poniżej abstrakcji" jest darmowe — to twój kod, zmieniasz co chcesz.
  `pydantic-ai` ma `direct.model_request()` i `WrapperModel`/custom `Model` jako escape hatch (docs
  potwierdzone), ale **każde zejście to nauka i utrzymanie DWÓCH warstw** — frameworka i tego, co
  pod nim. Ryzyko „utknięcia w połowie sezonu" jest **wyższe** przy B: gdy zadanie wymaga czegoś,
  czego `Agent` nie przewiduje, wracasz do `direct`/custom Model, czyli faktycznie do pisania tego,
  co w A masz od początku — tylko przez cudze API.

**Wniosek §5:** własny core ma escape hatch trywialny (to wszystko twój kod). B dokłada warstwę,
przez którą trzeba się przebić za każdym razem, gdy kurs wyłamie się ze schematu — a wyłamuje się
regularnie.

---

## 6. Wartość edukacyjna — po obu stronach

- **Własny core** = pełna transparentność mechanizmów (adapter, middleware chain, pętla agenta,
  structured output — wszystko widoczne i twoje).
- **Framework** = znajomość `pydantic-ai`, narzędzia realnie używanego w branży.

Rozstrzygnięcie: **argument edukacyjny za B aktywuje się dopiero po 20 flagach** — bo dopiero wtedy
wracamy do learning mode (`aid4u/CLAUDE.md`, baner EFFICIENCY MODE). **Flagi S03/S04 zdobywamy
TERAZ, w efficiency mode**, gdzie liczy się efekt, nie wartość poznawcza drogi. Czyli „nauka
frameworka branżowego" to wartość dla fazy, która jest **świadomie odłożona** — a wtedy migracja
będzie i tańsza (brak presji deadline'u 01.09) i lepiej umotywowana (uczysz się narzędzia, nie
ścigasz flagi). **Argument edukacyjny wspiera „zrób to później", nie „zrób teraz".**

Jedno taktyczne odstępstwo, które NIE łamie zakazu dwóch stacków: **e01 dosłownie nazywa się
„evaluation" i jego lekcja to observability+eval.** `pydantic-evals` (`Dataset`/`Case`/scoring) jest
już zainstalowany. Dopuszczam użycie go **jako izolowanego narzędzia pomiaru offline** w e01 —
**pod warunkiem** że: (a) nie wchodzi do ścieżki `solve()→submit()`, (b) nie zastępuje `LLMClient`
w runtime, (c) okaże się tańszy niż własny scoring na bazie `classify.py`. To biblioteka
ewaluacyjna działająca OBOK rdzenia, nie drugi runtime LLM — więc to nie jest „część zadań na B".
Jeśli okaże się, że wnosi tarcie zamiast oszczędności — pomijamy.

---

## 7. Odwracalność

- **A jest trywialnie odwracalne.** `pydantic-ai` już jest w `pyproject.toml` (zainstalowany:
  `2.18.0`, potwierdzone `uv pip list`). W dowolnym momencie dokładasz `Agent` do jednego zadania
  bez ruszania reszty. Nic nie tracisz, zależność zapłacona.
- **B jest drogie do cofnięcia** — zwłaszcza w połowie sezonu. Gdy w e04/e05 okaże się, że framework
  przeszkadza (własny format, deterministyka zamiast agenta), powrót do `LLMClient` znaczy: albo
  utrzymywać dwa stacki (zakazane), albo cofać migrację pod presją czasu. B1 dodatkowo: cofnięcie =
  porzucenie drugiego repo z całą przeniesioną infrą.

**A wygrywa odwracalność zdecydowanie.** To jest decyzja tania w jedną stronę (A→B kiedykolwiek)
i droga w drugą (B→A w połowie sezonu).

---

## 8. EFFICIENCY MODE — widoczny wpływ na decyzję

`aid4u/CLAUDE.md` (baner, od 2026-07-29): *„priorytet to WYŁĄCZNIE szybkość i skuteczność
zdobywania flag, aż do 20/25. (...) liczy się EFEKT, nie droga."* Do 20 flag brakuje S03+S04
(mamy 10). Ta reguła sama w sobie rozstrzyga większość czynników powyżej na korzyść A: migracja
frameworka jest z definicji inwestycją w *drogę* (czystość, ergonomia, znajomość narzędzia), a
tryb każe optymalizować *efekt* (flaga, czas). **Największa operacja wzmocnienia core do tej pory
(słowa `season.md`) jest dokładnie tym, czego efficiency mode każe nie robić teraz.**

---

## 9. B1 vs B2 — gdyby jednak B (rozstrzygnięte, nie machnięte ręką)

Autor „lekko preferuje B1". Policzone — **B1 jest najgorszym wariantem pod ten tryb, B2 lepszym:**

| Koszt | B1 (nowe repo) | B2 (nadbudówka tu) |
|---|---|---|
| Przeniesienie infry niemigrowalnej (§3) | **~1247 LOC ręcznie** | 0 — zostaje |
| Drzewo `AGENTS.md` (DOX) | **drugi komplet ~11 plików** | istniejące, aktualizowane |
| Deploy | **drugi** (systemd, ngrok, VPS) | jeden |
| Observability | **druga konfiguracja** Langfuse/Logfire | jedna |
| `run.py` / registry `@task` / `BaseTask` | **przepisać od zera** | refactor na miejscu |
| Zysk B1 ponad B2 | „czysty start na dzisiejszej wiedzy o kursie" | — |

„Czysty start" B1 kupujesz za **cały narzut zero-flagowy z tabeli**. W trybie, gdzie liczy się czas
do flagi, to najdroższa możliwa droga. **Gdyby decyzja padła na B — to B2, nie B1.** Ale rekomendacja
pozostaje **A** (§1-8).

---

## 10. Plan (po akceptacji — kod nie rusza wcześniej)

Kolejność zgodna z `season.md` (e03 → e01 → e04 → e05 → e02) i z routingiem commitów (`AGENTS.md:179`).

**Krok 0 — porządki kontraktowe w core (przed e02, nie przed e03).** Z `closed-prs-qodo-triage.md`
bierzemy **tylko to, co przeżywa przy A i wraca w S03**:

- **A1** (`BaseTask.run()` podwójny submit) — **wróci w S03**, bo e01/e02 mają iteracyjny/agentowy
  `solve()`. Zrobić przed e01.
- **A4** (`ToolCall.id` dublowany w Gemini) — dotyczy każdej pętli agentowej; zrobić przed e02.
- **Propagacja błędów narzędzia** (`client.py:137-139`) + **przepięcie `.structured()`/
  `run_agent_loop()` przez `self._chain`** (`client.py:73,117`) — to zamyka trzy z czterech luk §2
  jedną porcją roboty w `middleware`/`client`. Przed e01 (cost-tracking) i e02 (błędy, rate-limit).
- **Osłony e02** (rate limiter wychodzący `/api/*`, blacklist ścieżek w kodzie) — przed e02.
  Truncacja już jest (`feat/killswitch`).

**Nie robimy** (wyparowałoby przy B, więc i tak bez znaczenia — ale przy A po prostu poza zakresem
S03): nic z warstwy s01/s02 poza tym, co wyżej; A2/A3/A5/A6/A8 idą osobnym torem „contract hardening"
jeśli w ogóle (to nie blokuje flag S03).

**Krok 1 — e03 (reactor).** BFS/DP, zero LLM, zero stacku. Pierwsza flaga sezonu.

**Krok 2 — e01 (evaluation).** Batch: progi deterministyczne w kodzie, LLM tylko do sprzeczności
notatka↔dane, dedup notatek przed LLM (wzorzec s02e03). Tu — i tylko tu — rozważyć `pydantic-evals`
per §6.

**Krok 3-5 — e04, e05, e02** wg `s03eXX.md` (prep-faza per zadanie).

---

## Podsumowanie w jednym akapicie

Zostajemy przy własnym `core/`. Z pięciu zadań S03 jedno jest algorytmem (e03), jedno batchem (e01),
jedno budowaniem endpointu dla cudzego agenta (e04) — w żadnym z tych trzech `pydantic-ai` nic nie
wnosi. Zostają e02 (jednoznaczna pętla agenta) i e05 (da się deterministycznie), przy czym
najważniejsze w e02 — osłony pętli — trzeba napisać ręcznie niezależnie od stacku. Trzy z czterech
luk technicznych zamykamy tańszą łatką w `core/` niż migracją. EFFICIENCY MODE każe optymalizować
czas do flagi, a migracja kosztuje pierwsze dwie flagi sezonu bez zysku dla nich i odrabia się
najwcześniej w S04. A jest w dodatku trywialnie odwracalne (zależność już zapłacona), a B — zwłaszcza
B1 — drogie do cofnięcia. `pydantic-ai` wraca do rozmowy po 20 flagach, w learning mode, taniej i
z lepszym uzasadnieniem edukacyjnym.
