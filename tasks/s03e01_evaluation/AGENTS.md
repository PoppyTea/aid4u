# s03e01_evaluation Module

## Purpose
10 000 odczytów sensorów elektrowni → zgłoś ID plików z anomalią. Cztery reguły
anomalii z `doc/zadanie.md` zwijają się algebraicznie: `data_bad` (reguły #1 poza
zakresem + #4 zwraca dane których nie powinien, obie deterministyczne) ∨
`note_failure` (notatka zgłasza problem, jedyna rola LLM). Reguła #2 jest
podzbiorem `data_bad`, więc suma jest dwuskładnikowa, nie czteroskładnikowa. Pełne
wyprowadzenie: `solution.py` docstring.

**Rozwiązane (2026-08-16)** — flaga `{FLG:???}` w `.flags.json` (uzupełnić po
realnym submicie), model `claude-haiku-4-5-20251001` (wybrany po A/B, patrz
Verification).

## Ownership
- `solution.py`: `EvaluationTask` — `@task("s03e01", hub_name="evaluation")`.
- `readings.py`: reguły #1/#4, zero tokenów — progi i mapowanie `sensor_type`→pole
  wzięte WPROST z treści zadania, nie wyprowadzane z danych.
- `notes.py`: drabina dedupu (surowe notatki → unikalne notatki → unikalne frazy),
  podział na frazy, mapowanie indeksów batcha, bez LLM.
- `prompts.py`: prompt klasyfikatora fraz — jedyne miejsce z LLM w całym zadaniu.
  Zarejestrowany w Langfuse (`sync_prompt`, nazwa `s03e01-phrase-classifier`).
- Dane wejściowe: `GET dane/sensors.zip` przez `hub.get_public()`
  (`core/hub/client.py:186`). Zapisane raz do `data/input/s03e01_evaluation/sensors.zip`
  (commitowane — patrz `data/AGENTS.md`), nigdy nie rozpakowywane na dysk.
- `doc/`: treść zadania (`zadanie.md`, `fabula.md`) + destylat komentarzy kursu
  (`community_notes.md`) — materiał referencyjny, nieużywany w runtime.

## Local Contracts
- Odpowiedź to `{"recheck": [...]}` (obiekt, nie goła tablica) — string ID z
  zerami wiodącymi (`"0001"`), zgodnie z formatem z `doc/zadanie.md`.
- **Kontrakt jednostrzałowy**: treść zadania wymaga "w jednym zapytaniu" kompletnej
  listy ID. `solve()` NIE prowadzi własnej pętli `/verify` — `BaseTask.run()`
  wysyła odpowiedź dokładnie raz. A1 (`core/tasks/base.py:119`, podwójny submit)
  tu nie dotyczy — nie dokładać pętli retry z innymi progami.
- **Cache i artefakty są namespaced po modelu** (`phrase-label:{model}:{fraza}` w
  `.cache/`, `phrase_labels-{model}.json` w `data/output/`) — etykieta failure/OK
  ZALEŻY od modelu (to jest cały sens A/B), więc klucz bez modelu byłby
  niepoprawnym cache'owaniem: przełączenie `-m` po cichu czytałoby etykiety innego
  modelu zamiast klasyfikować ponownie. Znaleziono i naprawiono 2026-08-16 podczas
  właśnie takiego eksperymentu A/B.
- Koszt jest teraz śledzony NAPRAWDĘ (nie ręcznym `tiktoken`-em) — `llm.structured()`
  przechodzi przez `CostTrackMiddleware` od `feat/core-observability-langfuse`
  (`core/AGENTS.md`), więc `cost_usd` pojawia się w Logfire automatycznie dla
  każdego batcha.

## Work Guidance
- **Reguły #1/#4 są w 100% deterministyczne — LLM nigdy nie widzi odczytu.**
  Świadomie pominięte: profilowanie rozkładów (kwantyle, detekcja przerw w ogonie)
  do wyprowadzania progów — niepotrzebne, bo progi są podane wprost.
- **Klasyfikuj frazy (~325 na żywych danych), nie notatki (~2032) ani pliki
  (9999).** To jest cały cost-optimization tego zadania — patrz `doc/community_notes.md`.
- Punkty kontrolne z konsensusu społeczności trafione DOKŁADNIE na pierwszym
  realnym przebiegu: `deterministic_total=46` (konsensus ~46), `by_note_only=6`
  (konsensus ~6), `unique_phrases=325` (konsensus ~261, w oczekiwanym zakresie —
  dane różnią się per sesja/apikey, jak w `s02e03_failure`).
- **`--dry-run` WYWOŁUJE LLM naprawdę** (koszt realny, ~$0.003-0.008) — pomija
  tylko finalny `hub.submit()`. To jest zamierzone: punkty kontrolne mają sens
  tylko na prawdziwej klasyfikacji, nie symulowanej.

## Verification
- Zadanie zwraca flagę z huba — to ostateczna weryfikacja, nie zielone testy.
- **A/B przeprowadzone 2026-08-16** (`--dry-run` na żywych danych, ten sam prompt,
  4 batche, 325 fraz):

  | Model | Zgodność z drugim | Koszt | Czas |
  |---|---|---|---|
  | `claude-haiku-4-5-20251001` | 100% (0 sporów na 325 fraz) | $0.00753 | 5.3s |
  | `gemini-2.5-flash` | 100% (0 sporów na 325 fraz) | $0.00262 | 9.9s |

  Oba modele dały **identyczny finalny zbiór 52 anomalii** — brak sporów do
  rozstrzygnięcia punktem kontrolnym `by_note_only`. Wybrano `claude-haiku-4-5`
  (zgodny z domyślną drabiną `strategy/llm-selection.md`, szybszy) — koszt nie
  rozstrzygał, oba <1 centa, oba pod budżetem konsensusu (<2 centy).
- `uv run pytest tasks/s03e01_evaluation/` — 29 testów, zero wywołań LLM (czyste
  funkcje + kompozycja `data_bad ∨ note_failure`, w tym nazwany test na pułapkę
  pojęciową #3: `test_perfect_data_with_failure_note_is_anomaly`).
- `uv run run.py solve s03e01 --dry-run --model claude-haiku-4-5-20251001` —
  pełny przebieg przeciw żywemu hubowi, bez finalnego submitu.
- `uv run pyrefly check tasks/s03e01_evaluation/` — zielone.

## Child DOX Index
- None.
