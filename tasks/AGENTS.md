# Tasks Module

## Purpose
Execution environment for AI_Devs 4 course tasks. **Sezon 1 i Sezon 2 zamknięte** —
9 flag w `.flags.json` (s01e01, s01e02, s01e04, s01e05, s02e01…s02e05); s01e03 zaliczone
przez żywą rozmowę (ngrok/proxy), flaga poza `.flags.json` z natury tego typu zadania —
patrz `s01e03_proxy/AGENTS.md`. Szczegóły każdego epizodu (wzorzec danych, model użyty,
pułapki) żyją w jego własnym `AGENTS.md`, nie tutaj — Child DOX Index niżej wskazuje który.

**Sezon 3 ZAMKNIĘTY 5/5** (2026-08-16 → 2026-08-20) — kolejność ataku
`e01 → e03 → e04 → e05 → e02` zadziałała: e02 na końcu, po zbudowaniu czterech osłon
(AID-62/46/18/47). Cały sezon zero LLM w rozwiązaniach, łączny koszt ~$0.00. Stan gotowości, dług i checklisty per-epizod: `tasks/s03/requirements/`.
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
— **solved** (2026-08-16) — flaga `{FLG:BUGGYSYSTEM}`, za pierwszej próby, pierwsza
flaga sezonu. Reguły anomalii zwijają się do `data_bad ∨ note_failure`; LLM
klasyfikuje wyłącznie unikalne frazy notatek (~325 na żywych danych, nie 9999
plików). A/B Haiku 4.5 vs Gemini 2.5 Flash: 100% zgodności, wybrano Haiku.
`s03e04_negotiations/` — **solved** (2026-08-19) — flaga `{FLG:WINDFARM}`, trzecia
flaga sezonu, koszt $0.00. Odwrócone role: my wystawiamy 2 narzędzia HTTP (port 8004), agent
Centrali je odpytuje i sam zgłasza znalezione miasta (wynik: Domatowo + Skolwin,
6 z 10 dostępnych kroków). Zero LLM — dopasowanie po rdzeniach tokenów obsługuje
polską odmianę. Hub wymaga DOKŁADNIE 2 narzędzi i
klucza `URL` wielkimi literami; odpowiedź 4–500 B, brak odpowiedzi = agent
przerywa pracę. `s03e05_savethem/` — **solved** (2026-08-20) — `{FLG:INTACTCITY}` za pierwszym
podejściem + flaga sekretna `{FLG:ABEAVER}`, koszt $0.00. Zero LLM: front Pareto po
`(wiersz, kolumna, tryb)` nad dwoma niezależnymi budżetami. `dismount` jest warunkiem
KONIECZNYM — żaden pojedynczy tryb nie mieści się w budżecie na 11 ruchach. Dwie
pułapki potwierdzone na żywo: budżet OSTRY (zużycie 10.0 = porażka) i backend
indeksujący od 1 przy mapie od 0. `s03e02_firmware/` — **solved** (2026-08-20) — flaga `{FLG:CANTTOUCHTHIS}`, domyka
sezon. Zero LLM mimo że zadanie sugeruje pętlę agentową: po sondzie `help` przestrzeń
problemu okazała się mała i deterministyczna. Bramka poleceń (`command_guard`) odrzuciła
`rm`, `reboot` i wszystkie ścieżki z `.gitignore` — hasło leży w `/home/operator/notes/`,
NIE w `.env`, który jest pułapką na bana. `s03e03_reactor/` — **solved** (2026-08-17) — flaga `{FLG:INSTALLED}`, druga flaga
sezonu, 9 ruchów, 0 zgnieceń, koszt $0.00. Deterministyczny receding-horizon BFS,
zero LLM (najłatwiejszy epizod sezonu — LLM praktycznie zbędny wobec czystego
algorytmu). Format API (`answer: {"command": ...}`, kolizja sprawdzana PO
przesunięciu bloków) ustalony empirycznie sondą — lekcja go nie podaje.

**Końcówka kursu (S04+S05, rekonesans 2026-08-20):** `s04/` — `requirements/` z rankingiem
**wszystkich 10 pozostałych zadań** (S04E01–E05 i S05E01–E05) i wyborem piątki dającej
certyfikat; nie kontener implementacji, patrz `s04/AGENTS.md`. Zakres celowo obejmuje oba
sezony naraz, bo wybór jest jeden i przekrojowy. Rekomendowana kolejność ataku:
`s05e03 → s04e05 → s04e03 → s04e04 → s05e04`, rezerwy `s04e02 → s04e01 → s05e05`,
odrzucone twardo `s05e02` (TTS+STT, niedeterministyczny walidator, $5/12 h) i `s05e01`
(vision/OCR — wymaga AID-59, „Odłożone"). Żadne z 10 zadań nie potrzebuje publicznego
endpointu ani embeddingów. Szczegóły i lista rzeczy do sprawdzenia empirycznie:
`s04/requirements/season.md`.
