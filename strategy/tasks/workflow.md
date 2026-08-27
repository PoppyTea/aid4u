# Strategia implementacji zadań (aid4u)

## Proces dekompozycji (Task Decomposition)
Formatu (JSON, atrybuty, adnotacje) **nie ma w repo** — mieszka w skillu
`004-cat-decompose-task`. Wcześniejszy wskaźnik był martwy — plik
`strategy/tasks/task-decomposition.md` nigdy nie powstał.

---

## Wzorzec implementacji (Template Method)
Każde zadanie realizowane jest jako klasa dziedzicząca po `BaseTask` z `core/tasks/base.py`.

### Minimalna struktura
```
tasks/sXXeYY_nazwa/
├── __init__.py          # eksport klasy
├── solution.py          # @task("sXXeYY") class MojaTask(BaseTask)
├── prompts.py           # stałe z promptami (opcjonalne)
└── test_solution.py     # TDD: najpierw testy
```

---

## Flow — AID4U Task Pipeline

> ⚠️ **Ten pipeline należy do trybu nauki i jest dziś ZAWIESZONY.** Obowiązujący tryb
> deklaruje baner w `AGENTS.md` w korzeniu repo; w efficiency mode TDD i planowanie przed
> kodem nie są wymogiem wstępnym. Sprawdź tryb, zanim potraktujesz poniższe kroki jako
> obowiązkowe — reguła „bliższy dokument rządzi szczegółami" nie znosi decyzji o trybie.

W trybie nauki: każde zadanie kursowe przechodzi przez ten pipeline, nie pomijaj kroków.

### 0. PLAN `writing-plans`
- Wygeneruj plan implementacji → `doc/superpowers/plans/sXXeYY.md`
  (⚠️ `/doc/` w korzeniu repo jest w `.gitignore`, więc plan zapisany tam NIE trafi do
  gita — traktuj go jako notatnik sesji, nie jako trwały zapis decyzji)
- Każdy checkbox z planu → task TW via `001-papaver-tw-integration` z `depends` na poprzedni krok
- Plan jest recovery mechanism — gdy sesja umrze, wiesz gdzie wróć

### 1. Research — `sXXeYY_001`
- Przeczytaj plik lekcji `sXXeYY_*.md`
- Zrozum wejście/wyjście zadania
- `uv run run.py solve sXXeYY --dry-run` — dla zadań `dry_run_mode = "safe"` pokazuje
  odpowiedź bez wysyłki; dla zadań protokołowych odmawia startu. Kontrakt:
  `core/AGENTS.md`, sekcja o `dry_run`
- DONE gdy: wiesz co przychodzi i co musisz odesłać

### 2. TDD — `sXXeYY_002/003` → skill: `test-driven-development`
- Napisz testy **przed** implementacją — testy failujące (czerwone) = stan **poprawny**
- Wzorce HTTP do hub.ag3nts.org: skill `api-testing` (request/response, error handling)
- `uv run pytest tasks/sXXeYY_*/test_solution.py -v` — upewnij się że failują
- DONE gdy: testy istnieją i failują

### 3. Implementacja — `sXXeYY_004`
- Model: nie wpisuj identyfikatora z pamięci — domyślny bierze `run.py`, a zasady wyboru
  i eskalacji są w `strategy/llm-selection.md`
- Dodaj instrumentację Langfuse PRZED pierwszym uruchomieniem: skill `langfuse-observability`
- `setup_observability()` jako pierwsza linia skryptu (reguła projektu)
- DONE gdy: `uv run pytest` → wszystkie testy zielone

### 4. Weryfikacja — `sXXeYY_005/006` → skill: `verification-before-completion`
- `uv run run.py solve sXXeYY --dry-run` (jeśli zadanie go wspiera — patrz krok 1)
- Skill `verification-before-completion` musi potwierdzić output zanim ogłosisz done

**Debugging branch — wybierz dokładnie jedno:**
```
Test PASSES ale output zły?  → promptfoo-evals  (problem promptu/LLM)
Test NIE przechodzi?          → systematic-debugging  (problem kodu)
```
Szczegóły: `strategy/skills/skill-activation.md` → sekcja "Critical Decision"

### 5. Submission — `sXXeYY_007`
- `uv run run.py solve sXXeYY` — wysyłka do hub.ag3nts.org
- Potwierdź flagę `{FLG:XXXXX}` w output lub `uv run run.py status`
- `001-papaver-tw-integration`: task done **dopiero po** potwierdzeniu flagi — nie wcześniej

---

## Zasady dla zadań wymagających VPS
- Wykorzystaj `ServerFactory` w `core/server/factory.py` (FastAPI)
- Używaj `./deploy/deploy.sh` do wdrażania na VPS
- Konfiguracja systemd w `deploy/systemd/`
- Pamiętaj o otwarciu portów (`ufw`)
