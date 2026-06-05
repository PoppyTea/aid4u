# Strategia implementacji zadań (aid4u)

## Proces dekompozycji (Task Decomposition)
Zobacz `strategy_task_decomposition_v1.0.0.md` dla szczegółów technicznych (format JSON, atrybuty, proces krok po kroku).

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

### Flow
1. **Research:** `sXXeYY_001` — czytanie, zrozumienie wejścia/wyjścia.
2. **TDD:** `sXXeYY_002/003` — testy jednostkowe (offline).
3. **Impl:** `sXXeYY_004` — implementacja w `solution.py`.
4. **Verify:** `sXXeYY_005/006` — `run.py solve sXXeYY --dry-run`.
5. **Submit:** `sXXeYY_007` — wysyłka, flaga `{FLG:XXXXX}`.

## Zasady dla zadań wymagających VPS
- Wykorzystaj `ServerFactory` w `core/server/factory.py` (FastAPI).
- Używaj `./deploy/deploy.sh` do wdrażania na VPS.
- Konfiguracja systemd w `deploy/systemd/`.
- Pamiętaj o otwarciu portów (`ufw`).
