> **ZARCHIWIZOWANE 2026-08-18** — pozycje z tego dokumentu wyekstrahowane do Linear (team Aid4u).
> Mapowanie stare-ID → AID-XXX:
>
> | Stare ID | AID-XXX | Tytuł |
> |---|---|---|
> | R6 (referencja, patrz `closed-prs-qodo-triage.md`) | [AID-15](https://linear.app/aid4u/issue/AID-15) | BaseTask.run() zawsze wysyła odpowiedź drugi raz |
> | R7 (referencja) | [AID-28](https://linear.app/aid4u/issue/AID-28) | s02e03_failure/s02e04_mailbox: except httpx.HTTPStatusError zbyt szeroki |
> | R8 (referencja) | [AID-29](https://linear.app/aid4u/issue/AID-29) | HubClient.get_data/get_public brak reraise=True |
> | A | [AID-30](https://linear.app/aid4u/issue/AID-30) | s02e03_failure: brak globalnego egzekwowania budżetu tokenów |
> | B | [AID-31](https://linear.app/aid4u/issue/AID-31) | s02e03_failure: render_line() nie sanityzuje \n/\r |
> | C | [AID-43](https://linear.app/aid4u/issue/AID-43) | Kosmetyka dokumentacji s02e03 |
> | H | [AID-44](https://linear.app/aid4u/issue/AID-44) | scripts/panic.sh nie wiąże PGID z konkretnym runem |
> | I | [AID-45](https://linear.app/aid4u/issue/AID-45) | test_killswitch.py:260 -- nieużywany 'stdout' |
>
> D, E, F, G — **nie migrowane**: D rozstrzygnięta decyzja (apikey w doc/zadanie.md zostaje),
> E i G ✅ zrobione (naprawione w `9efab61` przed mergem PR#64), F przesłanka fałszywa
> (`killswitch.py` sprawdza `is not None`, nie truthy — nie jest bugiem).
>
> Pełne opisy żyją teraz wyłącznie w Linear — ten plik zostaje jako historyczny ślad triage'u.

# Triage otwartych uwag CodeRabbit — PR #56, #64

**Data:** 2026-08-16 · **Zakres:** cztery PR-y z realnymi komentarzami inline od `coderabbitai[bot]`
w całej historii repo (#56, #57, #64, #65) — reszta PR-ów (bot-generowane sugestie #1-#21, feature
PR-y bez inline review) nie miała komentarzy CodeRabbit do przejrzenia. **Bot:** `coderabbitai[bot]`,
nie Qodo (Qodo-derived reguły są już w `.claude/review-rules.md`, R1-R8).

## Metoda

`gh api repos/PoppyTea/aid4u/pulls/<N>/comments` per PR, filtr po `user.login=="coderabbitai[bot]"`,
sprawdzone wobec `main` @ `3528dcb` (2026-08-16). PR #57 i #65 — prawie wszystkie znalezione
oznaczone `✅ Addressed in commits ...` przez samego CodeRabbit, pominięte tutaj. Poniżej wyłącznie
to, co nie ma tego oznaczenia i zostało zweryfikowane jako wciąż obecne w kodzie.

---

## PR #56 (`tasks/s02e03_failure`, zadanie zaliczone — `{FLG:SQUASHIT}`)

Pokrywa się z `.claude/review-rules.md` R6/R7 (potwierdzone tam niezależnie 14.08, tu ponownie
16.08) — nie duplikuję opisu, patrz ten plik. Nowe, nieujęte w R6-R8:

### A. Brak globalnego egzekwowania budżetu tokenów po restore/trim
`tasks/s02e03_failure/solution.py` — `_hard_trim()` (linie ~174-192) pomija przypięte (pinned)
opisy, a `_restore_component()` (linie ~225-243) tworzy nową odpowiedź bez ponownego sprawdzenia
rozmiaru. Werdykt CodeRabbit: żądanie do weryfikatora może przekroczyć twardy limit `<1500` tokenów
i nie potrafi się z tego wycofać po feedbacku o przepełnieniu.
**Mechanizm poprawki:** policzyć finalny `render_log(events)` (łącznie z pinned) i redukować/usuwać
kwalifikujące się zdarzenia aż zmieści się w budżecie; to samo po `_restore_component()`, przed
zbudowaniem `answer`.

### B. Brak wymuszenia jednej linii na skompresowany wpis
`tasks/s02e03_failure/solution.py` — `CompressedEntry.text` to zwykły `str`, `_apply_compression()`
wstawia go wprost do `events["desc"]`. Jeśli model wstawi `\r`/`\n`, jeden wpis rozbija się na kilka
linii `answer["logs"]`, łamiąc kontrakt huba ("jedno zdarzenie = jedna linia").
**Mechanizm poprawki:** normalizować tekst modelu (usunąć/zastąpić `\r`/`\n`) przed
`_apply_compression()`.

### C. Kosmetyka (niski priorytet)
- `tasks/AGENTS.md` — `≤1500-token` powinno być `<1500-token` (limit jest ostry, nie inkluzywny).
- `tasks/s02e03_failure/doc/community_notes.md` — literówki wykryte przez LanguageTool.
- `tasks/s02e03_failure/doc/community_notes.md:26` — blok JSON bez oznaczonego języka (markdownlint).

### D. Zweryfikowany, świadomie zignorowany — apikey w `doc/zadanie.md`
Betterleaks (skaner sekretów CodeRabbit) zgłosił wykryty klucz API w
`tasks/s02e03_failure/doc/zadanie.md` (URL + przykład JSON, format `7a6dcc7c-...`). **Zweryfikowane
2026-08-16: to prawdziwy format apikey huba** (nie fałszywy alarm co do formatu), najpewniej
skopiowany 1:1 z treści zadania kursu przy zapisie `doc/zadanie.md`. Autor: świadomie nie warte
uwagi — to klucz do huba kursowego (submitowanie zadań), nie sekret produkcyjny. **Nie
rotować/redagować bez nowej decyzji.**

---

## PR #64 (`core/runtime/killswitch.py`, kill switch)

### ~~E. `start_run()` nie czyści starego `.run/STOP`~~ ✅ Naprawione
`request_stop()` może utworzyć `.run/STOP`, gdy żadne zadanie nie jest aktywne (np. wywołane
przypadkiem albo po zakończonym już runie). Kolejny `solve` odpala `start_run()`, które nie usuwa
tego sentinela — nowy run pada na pierwszym `check_abort()` bez widocznej przyczyny.
**Mechanizm poprawki:** `start_run()` ma jawnie skasować `.run/STOP`, jeśli istnieje, na starcie.

**Zweryfikowane 2026-08-17 (prep s03e03): naprawione już w commicie `9efab61`, przed mergem PR #64
— nie po nim.** `core/runtime/killswitch.py:85` — `start_run()` woła
`_STOP_FILE.unlink(missing_ok=True)`, udokumentowane w docstringu funkcji (`:69-72`). Ten triage
(16.08) sprawdzał wobec `main`, ale dla tej pozycji weryfikacja nie wyszła.

### ~~F. `run.py --max-seconds 0` nie jest walidowane~~ ⚠️ Przesłanka fałszywa
CLI przyjmuje `0` i ujemne wartości bez błędu; `start_run(max_seconds=0)` w `killswitch.py`
traktuje `0` jako falsy i wyłącza budżet całkowicie — help text obiecuje twardy limit, więc `0`
powinno być błędem walidacji, nie cichym "brak limitu".
**Mechanizm poprawki:** walidacja w CLI (`run.py`), odrzucić `<= 0` z czytelnym komunikatem.

**Zweryfikowane 2026-08-17: "`0` jako falsy" nie jest prawdą o kodzie.** `killswitch.py:86`
sprawdza `max_seconds is not None`, nie truthy — `0` jest **świadomym** budżetem "przerwij
natychmiast", udokumentowanym w docstringu `start_run()` (`:74-76`) i pokrytym testami
(`test_killswitch.py:98,123`, `tests/core/tasks/test_base.py:125` — ten ostatni komentuje wprost,
że budżet=0 to jedyny deterministyczny sposób wymuszenia `AbortRun` w teście). Wartości ujemne
**są** odrzucane, `ValueError` w `killswitch.py:84`. Realnie otwarte zostaje tylko: `run.py` CLI
nie ma własnej walidacji przed przekazaniem do `start_run()` — dziś ujemna wartość i tak kończy
się czytelnym `Błąd: max_seconds musi być >= 0, ...` (przez `except Exception` w `run.py:114`),
tylko nie jako walidacja argumentu na poziomie CLI. Kosmetyka, nie bug — nie warte osobnej
poprawki.

### ~~G. Testy killswitcha dotykają prawdziwego `.run/`~~ ✅ Naprawione
`tests/core/runtime/test_killswitch.py` — `_PGID_FILE`/`_STOP_FILE` rozwiązywane na poziomie modułu,
więc testy czytają/piszą do repo's prawdziwego `.run/`. Ryzyko: `end_run()` w autouse fixture kasuje
`.run/current.pgid` prawdziwego aktywnego runu, `test_raises_after_request_stop` zapisuje prawdziwy
`.run/STOP` i przerywa aktywny run, jeśli `pytest` odpala się równolegle z `solve`.
**Mechanizm poprawki:** `monkeypatch` ścieżek modułu na `tmp_path` dla testów jednostkowych; zostawić
prawdziwy katalog wyłącznie dla testu POSIX/panic, który go faktycznie potrzebuje.

**Zweryfikowane 2026-08-17: naprawione już w commicie `9efab61`.** `test_killswitch.py:29-32` —
autouse fixture `_isolated_run_dir` robi `monkeypatch.setattr` na `_RUN_DIR`/`_PGID_FILE`/
`_STOP_FILE` → `tmp_path`, plus `os.setsid` zneutralizowany. Prawdziwy `.run/` zostaje tylko dla
`TestPanicScriptKillsEntireProcessGroup`, dokładnie zgodnie z sugerowanym mechanizmem poprawki.

### H. `scripts/panic.sh` nie wiąże PGID z konkretnym runem
Osłona przed zabiciem własnej grupy procesów istnieje, ale nie chroni przed **recyklingiem PID** —
jeśli `.run/current.pgid` zawiera nieaktualny PGID wskazujący dziś na inny proces, `panic.sh` może
zabić obcą grupę. Niskie realne ryzyko dzięki `os.setsid()` (izolacja), ale nie zerowe.
**Mechanizm poprawki (Heavy lift):** przechowywać identyfikator runu razem z PGID w
`killswitch.py`, walidować go w `panic.sh` przed wysłaniem sygnału.

### I. Kosmetyka
- `tests/core/runtime/test_killswitch.py:260` — nieużywany `stdout` (ruff `RUF059`), zmienić na `_stdout`.

---

## Plan (nie zrobione — do zrobienia w osobnym PR/sesji)

**Poprawiony 2026-08-17** — poprzednia wersja tego planu (`E → A/B → F/G → H`) opierała się na
trzech pozycjach (E, F, G), które okazały się już zamknięte przy weryfikacji przed s03e03 (patrz
sekcje wyżej). Realnie otwarte: **R6/R7** (`.claude/review-rules.md` — podwójna submisja i szeroki
`except` w `s02e03_failure`, oba nadal obecne w kodzie) → **A/B** (poprawność odpowiedzi s02e03,
choć zadanie już zaliczone) → **H** (heavy lift, niski priorytet realny) → **C/I** (kosmetyka, przy
najbliższej okazji edycji tych plików).

R8 (`.claude/review-rules.md` — brak `reraise=True` w 3 metodach `HubClient`) zweryfikowany
2026-08-17: `grep -n "except.*httpx" tasks/ core/` zwraca tylko dwa miejsca (`s02e03_failure:270`,
`s02e04_mailbox:165`), oba wokół `submit()`/`post_api()` — **żadne** wokół `get_data`/`get_public`,
czyli metod bez `reraise=True`. Dziś nikogo to nie gryzie; warte ujednolicenia jako porządek, nie
jako naprawa (dokładnie kryterium, które R8 sam sobie postawił).
