# Tasks Module

## Purpose
Execution environment for AI_Devs 4 course tasks. **Sezon 1 zamknięty (2026-08-03)** —
s01e01, s01e02, s01e04, s01e05 zaliczone przez normalny `solve()→submit()` (flagi w
`.flags.json`); s01e03 zaliczone przez żywą rozmowę (ngrok/proxy) — flaga poza
`.flags.json`, patrz `s01e03_proxy/AGENTS.md`.

**Sezon 2 w toku (od 2026-08-03)** — tematy wszystkich 5 epizodów rozpoznane przez
NotebookLM (`LLM_aid4u_tylko_zadania`) i foldery przemianowane z sufiksem
tematycznym: `s02e01_categorize`, `s02e02_electricity`, `s02e03_failure`,
`s02e04_mailbox`, `s02e05_drone`. Sposób zdobycia danych wejściowych dla
wszystkich pięciu ustalony z wyprzedzeniem i zapisany w ich `AGENTS.md`
(Ownership) — zanim ruszyliśmy z implementacją którejkolwiek `solve()`. Wzorzec
skopiowany z dojrzałej wersji z sezonu 1 (e03–e05: `AGENTS.md`+`doc/`+`solution.py`
od startu) celowo, żeby uniknąć przemeblowań jakie miały miejsce przy e01/e02
(brak `AGENTS.md`/`doc/`, scratch pliki, niespójne nazwy danych). **s02e01
zaliczone (2026-08-03)** — flaga `{FLG:SMUGGLER}` w `.flags.json`. **s02e02
zaliczone (2026-08-05)** — flaga `{FLG:ROTATEIT}` w `.flags.json`, zdobyta ręcznie
przez lokalny `webui/` (rotacja planszy przez przeglądarkę), `solution.py`
automatyzujący `solve()→submit()` jeszcze nie istnieje. **s02e03 zaliczone
(2026-08-07)** — flaga `{FLG:SQUASHIT}` w `.flags.json`, przez normalny
`solve()→submit()` z pętlą iteracji wbudowaną w `solve()` (patrz
`s02e03_failure/AGENTS.md`). **s02e04 zaliczone (2026-08-07)** — flaga
`{FLG:TRAITOR}` w `.flags.json`, agentowa pętla function-calling (`LLMClient.run_agent_loop`)
przeszukująca żywe API `zmail`; `claude-haiku-4-5` zawiódł 3x pod rząd, `claude-sonnet-5`
rozwiązał od razu — patrz `s02e04_mailbox/AGENTS.md` dla realnego protokołu `zmail` (odkrytego
na żywo, różni się od tego co sugerowały komentarze kursu) i dla poprawki 429-resilience w
`HubClient.post_api()`. e05 czeka.

**EFFICIENCY MODE aktywny** (od 2026-07-29)
— priorytet: szybkość i skuteczność zdobywania flag do 20/25, nie proces. Learning-mode
wersja tego pliku: `.help/learning-vs-efficiency/learning-mode/aid4u/tasks/AGENTS.md`
(przywróć przez `aid4u/scripts/learning_mode_on_off.py on`).

## Ownership
- Each folder (`sXXeYY`) acts as a domain for a specific task.
- `s03/` (new as of 2026-08-08): first folder under `tasks/` grouping at the SEASON
  level rather than per-episode — holds `requirements/` only (pre-season readiness
  report + per-episode checklists), not task implementations. Season-3 task folders
  themselves stay flat (`tasks/s03e01_evaluation/` etc.), matching S01/S02. See
  `s03/AGENTS.md` and `strategy/season-transition.md` for the procedure this
  instantiates.

## Local Contracts
- Every task solution MUST contain `solution.py`. **Exception during season kickoff:**
  freshly-scaffolded episode folders (`AGENTS.md`+`doc/`+`__init__.py` only, `solution.py`
  explicitly marked "do utworzenia") are intentional — we go episode-by-episode per the
  acquisition-first workflow below, not all-at-once. Flagged by Qodo on PRs #52/#53
  (rule 1518473) and confirmed as a false positive both times — don't re-raise without
  new information.
- `test_solution.py` opcjonalny — pisz go PO działającym rozwiązaniu, tylko jeśli faktycznie
  pomoże zweryfikować coś nietrywialnego. Weryfikacja przez realne uruchomienie
  (`--dry-run` / hub) liczy się bardziej niż testy jednostkowe.
- Task execution via `uv run run.py solve sXXeYY`.
- **Wyjątek — zadania oparte na żywym serwerze (np. `s01e03_proxy`):** jeśli zadanie
  rozwiązuje się przez publicznie wystawiony endpoint (bot Centrali prowadzi rozmowę
  na żywo), a nie przez pojedyncze `fetch→solve→submit`, `solve()` MUSI jawnie
  odmówić (`raise RuntimeError` z instrukcją uruchomienia) zamiast po cichu wysyłać
  pustą/fałszywą odpowiedź na hub. Taki folder dostaje własny `AGENTS.md` (patrz
  Child DOX Index) opisujący kontrakt endpointu, zmienne środowiskowe i workflow.

## Work Guidance
- Zanim zaprojektujesz rozwiązanie od zera: sprawdź `4th-devs/` (fork
  `github.com/PoppyTea/4th-devs-fork`) pod kątem gotowego demo dla tego tematu — przepisz
  na Python zamiast wymyślać ponownie.
- Sposób rozwiązania nie musi być zgodny z założeniem zadania — liczy się flaga.
- Skonsultuj NotebookLM (komentarze + zadania kursu) jeśli utknąłeś lub szukasz
  najkrótszej drogi.
- **Przy starcie nowego sezonu:** najpierw dla WSZYSTKICH epizodów ustal sposób
  zdobycia danych wejściowych (endpoint, auth, statyczne czy żywe/mutowalne, cache
  czy nie) i zapisz w ich `AGENTS.md` (Ownership) — dopiero potem implementuj
  `solve()` dla kolejnych epizodów po kolei. Unika sytuacji gdzie zaczynasz kodować
  jeden epizod bez wiedzy czy dane innego wymagają zupełnie innego podejścia
  (statyczny plik vs żywe API vs `data/input/` z dokumentem referencyjnym).
  Potwierdzone przy starcie S02 (2026-08-03).
- **Gdzie zapisywać dane zadania** (ujednolicone 2026-08-05, patrz `data/AGENTS.md`):
  `.cache/` to WYŁĄCZNIE efemeryczny cache przyspieszający TDD (hash-named,
  `rm -rf` bezpieczne, nigdy jedyne miejsce trzymania czegoś wartościowego).
  Cokolwiek pobrane/wyprodukowane, co może przydać się w PÓŹNIEJSZYM epizodzie,
  idzie do `data/input/sXXeYY_nazwa/` (pobrane) lub `data/output/sXXeYY_nazwa/`
  (wyprodukowane/wyliczone) — commitowane, czytelne nazwy. `data/run-history/`
  jest automatyczne (`BaseTask._save_output`) i jednorazowe — nigdy nie czytaj
  go jako źródła danych dla innego zadania.
- **Nie lekceważ fabuły.** To normalny, merytoryczny element treści zadania, nie
  ozdobnik do pominięcia — czytaj ją tak samo uważnie jak specyfikację techniczną.
  Potrafi zawierać konkretne dane potrzebne do rozwiązania (nazwy, słowa kluczowe,
  kontekst rozstrzygający niejednoznaczność), a czasem fabuła jednego zadania
  ujawnia informacje istotne dla innego (np. s01e03 pozwala wywnioskować element
  odpowiedzi z s01e02). Potwierdzone dwukrotnie w praktyce (2026-08-01).

## Verification
- Zadanie zwraca flagę z huba — to jest ostateczna weryfikacja, nie zielone testy.

## Child DOX Index
- `s01e02_findhim/`: solved — data entirely live (hub + Nominatim geocoding at
  solve-time), no static input files; see that folder's `AGENTS.md` for the
  2026-08-05 dead-scratch-data cleanup.
- `s01e03_proxy/`: live-server task (public `/` endpoint) — see local exception above.
- `s01e04_sendit/`: deterministic SPK declaration builder, no LLM.
- `s01e05_railway/`: multi-step hub API protocol (route activation), no LLM —
  503/429 resilience lives in `HubClient.submit()`, not here.
- `s02e01_categorize/`: **solved** — prompt-only classification task (DNG/NEU,
  ≤100 tokens), no LLM at runtime. `answer` must be `{"prompt": ...}` (JSON
  object, undocumented) and DNG must stay scoped to actual weapons, not
  anything hazardous-sounding — see that folder's `AGENTS.md` for the live
  failure that taught this.
- `s02e02_electricity/`: **solved** (manually, via local `webui/`) — 3x3
  pipe-rotation puzzle, image-driven, live/mutable board state (re-fetch after
  every `rotate`). `solve()` automation still outstanding.
- `s02e03_failure/`: **solved** — huge log file → ≤1500-token condensed
  summary. Mostly deterministic (dedup + `[INFO]` filter in code collapses
  2137 raw lines to 55 before any LLM call); the hub's iterative
  accept/reject feedback loop lives inside `solve()` itself, not in
  `BaseTask.run()` — see that folder's `AGENTS.md` for the `/verify` HTTP 400
  contract and the token-budget-instruction-doesn't-work lesson.
- `s02e04_mailbox/`: **solved** — agentowa `run_agent_loop()` przeszukuje żywe API `zmail`
  (protokół odkryty na żywo przez `help`: help/getInbox/getThread/getMessages/search/reset).
  `claude-sonnet-5` wymagany — `claude-haiku-4-5` konsekwentnie kończył pętlę bez wysyłki
  odpowiedzi. Zobacz też `HubClient.post_api()` 429-retry (`core/AGENTS.md`), dodany bo zmail
  faktycznie rate-limituje mimo że treść zadania tego nie wspominała.
- `s02e05_drone/`: static reference docs (HTML API doc + terrain map) — only S02
  episode qualifying for a `data/input/` subfolder so far.
- `s03/`: season-3 readiness report + per-episode checklists (`requirements/`) — see
  `s03/AGENTS.md`. Not a container for task implementations, see Ownership above.
