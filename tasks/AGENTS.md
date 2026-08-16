# Tasks Module

## Purpose
Execution environment for AI_Devs 4 course tasks. **Sezon 1 i Sezon 2 zamknięte** —
9 flag w `.flags.json` (s01e01, s01e02, s01e04, s01e05, s02e01…s02e05); s01e03 zaliczone
przez żywą rozmowę (ngrok/proxy), flaga poza `.flags.json` z natury tego typu zadania —
patrz `s01e03_proxy/AGENTS.md`. Szczegóły każdego epizodu (wzorzec danych, model użyty,
pułapki) żyją w jego własnym `AGENTS.md`, nie tutaj — Child DOX Index niżej wskazuje który.

**Sezon 3 w toku** (od 2026-08-16) — kolejność ataku `e01 → e03 → e04 → e05 → e02`
(e02 na końcu świadomie: najdroższe zadanie sezonu, wymaga osłon pętli agentowej których
jeszcze nie ma). Stan gotowości, dług i checklisty per-epizod: `tasks/s03/requirements/`.
Procedura przejścia między sezonami (sezonoagnostyczna): `strategy/season-transition.md`.

**EFFICIENCY MODE aktywny** (od 2026-07-29) — priorytet: szybkość i skuteczność
zdobywania flag do 20/25, nie proces. Learning-mode wersja tego pliku:
`.help/learning-vs-efficiency/learning-mode/aid4u/tasks/AGENTS.md`
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

**Sezon 1** (solved): `s01e02_findhim/` (live geocoding, no static input) ·
`s01e03_proxy/` (live-server exception, see Local Contracts) ·
`s01e04_sendit/` (deterministic, no LLM) · `s01e05_railway/` (multi-step hub protocol, no LLM).

**Sezon 2** (solved, 5/5): `s02e01_categorize/` (prompt-only, no runtime LLM) ·
`s02e02_electricity/` (solved manually via `webui/`, `solve()` automation outstanding) ·
`s02e03_failure/` (dedup+filter pattern, iterative `/verify`) ·
`s02e04_mailbox/` (agentowa `run_agent_loop()`, wymaga `claude-sonnet-5`) ·
`s02e05_drone/` (zero LLM, deterministic map analysis).

**Sezon 3** (w toku): `s03/` — readiness report + per-episode checklists
(`requirements/`), nie kontener implementacji, patrz Ownership. `s03e01_evaluation/`
— **solved** (2026-08-16, pierwsza flaga sezonu), reguły anomalii zwijają się do
`data_bad ∨ note_failure`; LLM klasyfikuje wyłącznie unikalne frazy notatek
(~325 na żywych danych, nie 9999 plików). A/B Haiku 4.5 vs Gemini 2.5 Flash: 100%
zgodności, wybrano Haiku.
