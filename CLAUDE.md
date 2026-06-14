# CLAUDE.md — Projekt AI_Devs 4 (aid4u)

Centralny indeks projektu. Ten plik to zbiór wskaźników — szczegóły są w plikach docelowych.

---

## 🚀 Szybki start
- **Zadanie dnia:** `task focus` → znajdź folder w `/tasks` → `uv run run.py solve sXXeYY`
- **Nowe zadanie kursowe:** zacznij od `writing-plans`, nie od kodu
- **Modele LLM:** domyślnie `gemini-2.5-flash` — szczegóły w `strategy/llm-selection.md`
- **Observability:** `setup_observability()` musi być zawsze w pierwszej linii skryptu
- **MCP:** używaj serwerów dokumentacji (`langfuse`, `logfire`, `context7`) zamiast bazować na treningu
- **Nazewnictwo plików:** `strategy/naming-conventions.md` — czytaj przed tworzeniem nowych plików

---

## 🗺️ Index

| Temat | Plik |
| :--- | :--- |
| **Strategia LLM / modele** | `strategy/llm-selection.md` |
| **Dekompozycja zadań (JSON + TW)** | `strategy/tasks/task-decomposition.md` |
| **Workflow implementacji + skille** | `strategy/tasks/workflow.md` |
| **Aktywacja skillów / trigger rules** | `strategy/skills/skill-activation.md` |
| **ADHD workflow + rescue patterns** | `strategy/tasks/adhd-workflow.md` |
| **Konwencje nazewnictwa plików** | `strategy/naming-conventions.md` |
| **Struktura infrastruktury** | `README.md` |
| **MCP serwery** | `.claude/settings.json` |

> Migracja nazw w toku — stare pliki (`strategy_llm_v1.0.0.md`, `strategy_task_decomposition_*`)
> działają do czasu przepisania. Po migracji usuń tę notatkę.

---

## 🧰 Skille — roster

| Skill | Kiedy |
|---|---|
| `writing-plans` | każde nowe zadanie — plan przed kodem |
| `test-driven-development` | pisanie testów, TDD, nowy feature |
| `systematic-debugging` | bug po 2+ próbach bez skutku |
| `verification-before-completion` | przed **każdym** `task done` |
| `langfuse-observability` | instrumentacja agenta, trace |
| `promptfoo-evals` | output zły mimo zielonych testów |
| `api-testing` | REST, hub.ag3nts.org patterns |
| `001-jeremy` | **każda** operacja TW bez wyjątku |
| `adhd-daily-planner` | start sesji, rytm dzienny |
| `project-management-guru-adhd` | blokada >15 min, overwhelm |
| *(więcej)* | pełna lista → `strategy/skills/skill-activation.md` |

---

## 🛠️ Architektura i Stack
- **Python 3.12+**, `uv` jako manager pakietów
- **Wzorce projektowe:**
  - `Strategy/Adapter` → `core/llm/adapters/`
  - `Template Method` → `core/tasks/base.py`
  - `Registry` → dekorator `@task`
  - `Chain of Responsibility` → `core/llm/middleware.py`

---

## ⚙️ Najczęstsze komendy
```bash
uv sync                          # instalacja środowiska
uv run run.py solve sXXeYY       # rozwiąż zadanie
uv run pytest                    # testy jednostkowe
./deploy/deploy.sh               # deployment na VPS
task focus                       # jedno zadanie — zawsze zaczynaj tutaj
```

---

## ⚠️ Zasady pracy

1. **TDD:** Testy PRZED implementacją. Napisałeś kod przed testem? Usuń kod, napisz test.
2. **LLMClient:** Nie używaj bezpośrednio SDK — tylko `LLMClient` z `core/llm/`.
3. **Observability:** `setup_observability()` zawsze jako pierwsza linia skryptu.
4. **Rate Limit:** `503` → użyj `hub.get_data_503_tolerant()`.
5. **Single focus:** Jeden task TW naraz. `task focus` — nie `task list`, nie pamięć.
