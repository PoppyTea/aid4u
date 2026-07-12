# Projekt AI_Devs 4 (aid4u)

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
| **Strategia LLM (wybór/eskalacja/tier)** | `strategy/llm-selection.md` |
| **Modele LLM (referencja/ściągawka)** | `strategy/llm-models.md` |
| **Dekompozycja zadań (JSON + TW)** | `strategy/tasks/task-decomposition.md` |
| **Workflow implementacji + skille** | `strategy/tasks/workflow.md` |
| **Aktywacja skillów / trigger rules** | `strategy/skills/skill-activation.md` |
| **ADHD workflow + rescue patterns** | `strategy/tasks/adhd-workflow.md` |
| **Konwencje nazewnictwa plików** | `strategy/naming-conventions.md` |
| **Struktura infrastruktury** | `README.md` |
| **MCP serwery** | `.claude/settings.json` |

> Migracja nazw w toku — stary plik `strategy_task_decomposition_v1.0.0.md`
> działa do czasu przepisania na `strategy/tasks/task-decomposition.md`. Po migracji usuń tę notatkę.
> (`strategy_llm_v1.0.0.md` → `strategy/llm-selection.md` + `strategy/llm-models.md`: zrobione.)

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

# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:
- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

## User Preferences

When the user requests a durable behavior change, record it here or in the relevant child AGENTS.md

## Child DOX Index

- `core/`: System architecture, LLM and task management base.
- `strategy/`: Project strategic documentation and workflows.
- `tasks/`: Task execution and course exercises.
- `tests/`: Project test suite and verification logic.
- `data/`: Task input datasets — safe-read rules per file.
- `../misje-poboczne/`: Side missions and specific project artifacts.

