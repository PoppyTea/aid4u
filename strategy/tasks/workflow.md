# Strategia implementacji zadań (aid4u)

## Proces dekompozycji (Task Decomposition)
Szczegóły techniczne (format JSON, atrybuty, adnotacje): `strategy/tasks/task-decomposition.md`

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

Każde zadanie kursowe przechodzi przez ten pipeline. Nie pomijaj kroków.

### 0. PLAN `writing-plans`
- Wygeneruj plan implementacji → `docs/superpowers/plans/sXXeYY.md`
- Każdy checkbox z planu → task TW via `001-jeremy` z `depends` na poprzedni krok
- Plan jest recovery mechanism — gdy sesja umrze, wiesz gdzie wróć

### 1. Research — `sXXeYY_001`
- Przeczytaj plik lekcji `sXXeYY_*.md`
- Zrozum wejście/wyjście zadania
- `uv run run.py solve sXXeYY --dry-run` — sprawdź co hub.ag3nts.org zwraca
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
- `uv run run.py solve sXXeYY --dry-run`
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
- `001-jeremy`: task done **dopiero po** potwierdzeniu flagi — nie wcześniej

---

## Zasady dla zadań wymagających VPS
- Wykorzystaj `ServerFactory` w `core/server/factory.py` (FastAPI)
- Używaj `./deploy/deploy.sh` do wdrażania na VPS
- Konfiguracja systemd w `deploy/systemd/`
- Pamiętaj o otwarciu portów (`ufw`)
