> **ZARCHIWIZOWANE 2026-08-18.** Decyzja podjęta 2026-08-16 →
> `tasks/s03/requirements/core-stack-decision.md` (Ścieżka A — zostajemy przy własnym
> `core/llm/`). Ten plik nigdy nie miał wyekstrahowanych issues (to prompt-decyzja, nie triage) —
> stąd brak tabeli mapowania. Zostaje jako historyczny ślad tego, jak decyzja została zamówiona.

# Prompt do osobnego wątku: decyzja architektoniczna pre-s03

> Skopiuj wszystko poniżej linii jako pierwszą wiadomość w nowym wątku.
> Wątek powinien startować w `/home/lis/projekty/10_izolowane_projekty/00_aid4u`.

---

Sesja `pre-s03`. Zadanie: **rozstrzygnąć, na czym budujemy sezon 3 i dalej** — na własnym
`core/llm/`, czy na ekosystemie `pydantic-ai`. To decyzja, nie burza mózgów: oczekuję jednej
rekomendacji z uzasadnieniem, nie przeglądu opcji.

Nie pisz kodu w tej sesji. Efektem ma być decyzja + plan, zapisany w
`aid4u/tasks/s03/requirements/` (nazwę pliku dobierz sam, zgodnie z `naming-conventions.md`).

## Stan wyjściowy — fakty, których nie musisz sprawdzać od zera

- **10 flag zdobytych** (9 w `.flags.json` + `s01e03` zdobyte żywą rozmową przez proxy, więc poza
  plikiem). Sezony 1 i 2 zamknięte. Do progu 20 flag — czyli do powrotu z EFFICIENCY MODE do
  learning mode — brakuje dokładnie sezonu 3 i 4.
- **`pydantic-ai` jest już w `pyproject.toml`** (`pydantic-ai>=2.18.0`, `pydantic-ai-slim[google,openai]`,
  `pydantic-ai-harness[logfire]`) i **nie jest importowane w ani jednym pliku `.py`**. Zapłacone,
  niepodłączone. To samo dotyczy `openai-agents`, `mcp`, `mem0ai`, `openapi-pydantic`, `prompt-toolkit`.
- **Ta decyzja jest już zidentyfikowana i opisana** jako „rozwidlenie drogi" w
  `tasks/s03/requirements/season.md` (linie ~77-87) i `tasks/s03/requirements/source/tool-inventory.md`
  (sekcja „`pydantic-ai` — rozwidlenie drogi, nie dołożenie zależności", linie ~130-144), z podziałem
  na Ścieżkę A (zostajemy przy własnym core) i Ścieżkę B (przechodzimy na pydantic-ai). **Zacznij od
  przeczytania obu tych dokumentów w całości** — nie odtwarzaj analizy, która już tam jest; rozstrzygnij ją.
- `core/` to **3186 LOC**. Podział, który ma znaczenie dla tej decyzji:
  - warstwa LLM (`adapters/`, `client.py`, `middleware.py`, `factory.py`, `types.py`, `base.py`,
    `classify.py`, 4 × `native_tool_*.py`) — to jest obszar pokrywający się z `pydantic-ai`,
  - `hub/` (`client.py` 258 LOC + `cache.py`) — protokół hub.ag3nts.org, **nic tego nie zastąpi**,
  - `secrets.py`, `config.py`, `observability/`, `runtime/killswitch.py`, `net.py`, `server/factory.py`
    — infrastruktura niezależna od tej decyzji.

## Poprawka do wcześniejszego ustalenia — przyjmij jako dane

Padło kiedyś stwierdzenie, że przejście na `pydantic-ai` wymagałoby przepisania `s01` i `s02`.
**To nieprawda i nie analizuj tego wariantu.** Zadania zamknięte nie wymagają migracji — flagi są
zdobyte, kod ma wartość wyłącznie archiwalną. Jedyne, co realnie przenosi się do przodu, to
`tasks/common/` oraz warstwa komunikacji z hubem. Koszt migracji liczy się **od dziś w przód**,
nie wstecz.

## Opcje do rozstrzygnięcia

1. **A — zostajemy przy własnym `core/`.** Wprowadzamy poprawki z
   `.issues/summaries-4-human/closed-prs-qodo-triage.md` i lecimy z s03/s04.
2. **B1 — nowe repo na `pydantic-ai`.** Rusztowanie budowane od zera na dzisiejszej wiedzy o kursie,
   z przeniesieniem tylko tego, co warte przeniesienia. *(lekko preferowane przez autora)*
3. **B2 — to samo repo, `pydantic-ai` jako nadbudówka.** Zachowujemy warstwę hubową, warstwa LLM
   przechodzi na framework.

## Czynniki, które MUSISZ rozważyć i nazwać wprost

Nie chcę samego werdyktu — chcę zobaczyć, na czym stoi. Każdy punkt niżej ma się pojawić w analizie
z konkretną odpowiedzią, a nie zostać pominięty:

1. **Pokrycie funkcjonalne, mierzone.** Które konkretnie moduły `core/llm/` stają się martwe przy B,
   ile to LOC, i ile jest miejsc wywołania (nie „dużo/mało" — liczby z `grep`).
2. **Czego s03 wymaga, a czego dzisiejszy core nie ma.** `tool-inventory.md` (sekcja „WYMAGAJĄCE
   UPGRADU") wylistował już cztery takie luki — m.in. dynamiczne odkrywanie narzędzi blokujące e05
   i omijanie middleware przez `.structured()`/`run_agent_loop()`, przez co cost-tracking nie działa
   akurat w e01, czyli w zadaniu *o koszcie*. Dla każdej luki: czy `pydantic-ai` daje to z półki,
   czy i tak trzeba dopisać?
3. **Co jest niemigrowalne.** Hub, killswitch, secrets, observability, deploy. Ile z tego trzeba
   przenieść ręcznie przy B1 (nowe repo) i ile to realnie kosztuje?
4. **Koszt mierzony czasem do pierwszej flagi s03e01**, nie „elegancją" ani „czystością". Ile dni
   opóźnienia kosztuje B, i czy odrabia się jeszcze w tym sezonie, czy dopiero w s04?
5. **Escape hatch.** Kurs regularnie wymaga rzeczy, których framework nie przewiduje (własny protokół
   huba, wymuszony format odpowiedzi, żywa rozmowa przez proxy jak w s01e03). Jak wygląda zejście
   poniżej abstrakcji `pydantic-ai`, kiedy zadanie tego wymaga? To jest pytanie o ryzyko zablokowania
   się w połowie sezonu, i traktuj je poważnie.
6. **Wartość edukacyjna po obu stronach.** Po 20 flagach wracamy do learning mode. Własny core =
   pełna transparentność mechanizmów. Framework = znajomość narzędzia używanego w branży. To nie jest
   oczywiste w żadną stronę — rozstrzygnij, nie zbywaj.
7. **Odwracalność.** Która decyzja jest tańsza do cofnięcia w połowie sezonu 3?
8. **B1 vs B2 osobno.** Jeśli rekomendujesz B, rozstrzygnij też podwariant. Nowe repo oznacza drugi
   zestaw AGENTS.md, drugi deploy, drugą konfigurację observability — policz to, nie machnij ręką.

## Wymagania wobec analizy

- **Każde twierdzenie ma mieć dowód.** Jeśli piszesz „X jest dobrym kandydatem na Y" — pokaż `grep`,
  liczbę, cytat z dokumentacji. Uzasadnienia, które tylko *brzmią* prawdopodobnie, są gorsze od ich
  braku, bo wyglądają jak ustalenie. To już się w tym projekcie zdarzyło i zostało wyłapane.
- **Sprawdź aktualny stan `pydantic-ai`**, nie polegaj na pamięci — użyj Context7 albo dokumentacji.
  Wersja w `pyproject.toml` to `>=2.18.0`; sprawdź, co ta wersja faktycznie ma (`TestModel`/`FunctionModel`
  do deterministycznych testów agentów, rejestr narzędzi, integracja z Logfire, streaming, multimodalność).
- **Treść zadań s03 czytaj ze źródła.** Wersja RAG jest w zeszytach NotebookLM (`nlm` CLI / MCP),
  dosłowna treść w repo `aid4u-private/` obok `aid4u/`. `tasks/s03/requirements/s03e0*.md` to destylat,
  nie oryginał — przy ocenie wymagań technicznych sięgnij po oryginał, zwłaszcza dla e04 i e05.
- **Uwzględnij `.issues/summaries-4-human/closed-prs-qodo-triage.md`** — kilka pozycji z sekcji A
  (A1 kontrakt `BaseTask.run()`, A4 `ToolCall.id`, A6 cost-tracking) przestaje mieć znaczenie przy
  Ścieżce B, bo dotyczy kodu, który by zniknął. Nie planuj pracy, która wyparuje.
- **DOX obowiązuje.** Przeczytaj łańcuch `AGENTS.md` przed edycją czegokolwiek i zrób pass po.
  Zwróć uwagę na EFFICIENCY MODE w `aid4u/CLAUDE.md` — priorytetem jest tempo zdobywania flag do 20,
  nie czystość architektury. Ta reguła ma realny wpływ na tę decyzję i ma być w analizie widoczna.
- Odpowiadaj po polsku.

## Czego nie robić

- Nie rozstrzygaj tego „na pół" (część zadań na A, część na B) bez bardzo mocnego uzasadnienia —
  dwa równoległe stacki to najgorszy możliwy wynik tej sesji.
- Nie sugeruj migracji `s01`/`s02`.
- Nie zaczynaj kodowania ani rusztowania, dopóki decyzja nie zostanie zaakceptowana przez autora.
