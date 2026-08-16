# Projekt AI_Devs 4 (aid4u)

Centralny indeks projektu. Ten plik to zbiór wskaźników — szczegóły są w plikach docelowych.

---

> ⚡ **TRYB: EFFICIENCY MODE** (od 2026-07-29) — priorytet to WYŁĄCZNIE szybkość i skuteczność
> zdobywania flag, aż do 20/25. Część edukacyjna świadomie zeszła na drugi plan. Sposób
> rozwiązania NIE MUSI być zgodny z założeniem/duchem zadania — liczy się EFEKT, nie droga.
> Stary tryb (nauka, TDD-first, pełne planowanie przed kodem) jest schowany, nie usunięty —
> `.help/learning-vs-efficiency/learning-mode/` + `aid4u/scripts/learning_mode_on_off.py on`
> przywraca go nieddestrukcyjnie. Kurs ma nadal służyć edukacyjnie po zdobyciu 20 flag —
> to świadomy, tymczasowy kompromis, nie zmiana celu.

> ✅ **Sezon 1 + Sezon 2 zamknięte, Sezon 3 w toku** — 10 flag w `.flags.json`
> (`run.py status` pokaże 10/11 — `s01e03_proxy`, żywy serwer/ngrok, strukturalnie
> nie przechodzi przez `solve()→submit()`, więc jego flaga nigdy nie trafia do
> pliku; cecha tego typu zadania, nie błąd). **s03e01 zaliczone (2026-08-16)** —
> `{FLG:BUGGYSYSTEM}`, pierwsza flaga sezonu, za pierwszej próby. Kolejność ataku
> `e01 → e03 → e04 → e05 → e02` (e02 na końcu świadomie, patrz
> `tasks/s03/requirements/season.md`), stack własny `core/llm/` (nie `pydantic-ai`,
> patrz `core-stack-decision.md`). Szczegóły i checklisty: `tasks/s03/requirements/`.

## 🚀 Szybki start (efficiency mode)
- **Zadanie dnia:** znajdź folder w `/tasks` → `uv run run.py solve sXXeYY`
- **Nowe zadanie kursowe — PRZED pisaniem czegokolwiek:**
  1. Sprawdź `4th-devs/` (fork: `github.com/PoppyTea/4th-devs-fork`) — jeśli jest gotowe demo
     dla tego tematu, przepisz je na Python zamiast projektować od zera.
  2. Skonsultuj NotebookLM (komentarze kursu + notatnik zadań) — nierzadko ktoś już opisał
     jak przejść zadanie w godzinę-dwie. To pierwsze źródło, nie ostatnie.
  3. Dopiero jeśli powyższe nic nie dają — projektuj sam, najkrótszą ścieżką do flagi.
- **Modele LLM:** domyślnie `claude-haiku-4-5-20251001` (drabina Claude — szczegóły w
  `strategy/llm-selection.md`). Jeśli zauważysz że zadanie skorzystałoby na mocniejszym
  modelu (Sonnet 5 → Opus 5 → Fable 5) — zgłoś to natychmiast, nie męcz się słabszym.
- **Subagenci / równoległość:** jeśli zadanie jest na tyle proste, że masz pewność iż
  poradzi sobie Haiku 4.5 — zaproponuj zlecenie albo sam wyślij subagenta. Rozważ pracę nad
  kilkoma zadaniami równolegle, jeśli to przyspieszy dojście do 20 flag.
- **Observability:** `setup_observability()` musi być zawsze w pierwszej linii skryptu
- **Nazewnictwo plików:** `strategy/naming-conventions.md` — czytaj przed tworzeniem nowych plików

---

## 🗺️ Index

| Temat | Plik |
| :--- | :--- |
| **Strategia LLM (wybór/eskalacja/tier)** | `strategy/llm-selection.md` |
| **Modele LLM (referencja/ściągawka)** | `strategy/llm-models.md` |
| **Protokół nauki (zarchiwizowany, efficiency mode)** | `strategy/learning-protocol.md` |
| **Konwencje nazewnictwa plików** | `strategy/naming-conventions.md` |
| **Sekrety / keyring** | `strategy/secrets-management.md` |
| **Struktura infrastruktury** | `README.md` |
| **MCP serwery** | `.claude/settings.json` |

---

## 🧰 Skille — roster (efficiency mode)

| Skill | Kiedy |
|---|---|
| `verification-before-completion` | przed **każdym** `task done` — nawet szybko, sprawdź że faktycznie działa |
| `systematic-debugging` | bug po 2+ próbach bez skutku |
| `langfuse-observability` | instrumentacja agenta, trace |
| `api-testing` | REST, hub.ag3nts.org patterns |
| `001-jeremy` | **każda** operacja TW bez wyjątku |

Pełny roster trybu nauki (`writing-plans`, `test-driven-development`, `adhd-daily-planner`
itd.) jest w zarchiwizowanej wersji tego pliku — patrz baner na górze.

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

## ⚠️ Zasady pracy (efficiency mode)

1. **Efekt > droga.** Sposób rozwiązania nie musi być zgodny z założeniem zadania — liczy
   się zdobyta flaga. TDD/planowanie nie są zabronione, ale nie są już wymogiem wstępnym.
2. **4th-devs najpierw.** Przed projektowaniem nowego rozwiązania sprawdź `4th-devs/`
   (fork, TypeScript) — gotowe demo do przepisania na Python bije projektowanie od zera.
3. **LLMClient:** Nie używaj bezpośrednio SDK — tylko `LLMClient` z `core/llm/`.
4. **Observability:** `setup_observability()` zawsze jako pierwsza linia skryptu.
5. **Rate Limit:** `503` → użyj `hub.get_data(path, tolerate_503=True)`.
6. **Single focus:** Jeden task TW naraz. `task focus` — nie `task list`, nie pamięć.

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

- **Commit routing (soft guideline, not a hard gate):** any change to code files (`.py` — app or tests, including refactors and non-behavioral cleanups, not just logic fixes) goes through a feature branch + PR — this triggers CodeRabbit (PR overview + inline findings). Everything non-code (markdown docs, config files like `pyproject.toml`, symlinks, data files) commits straight to `main`. Trivial comment/docstring-only edits riding along inside an otherwise doc-focused commit are fine to leave on `main`. Override locally in a child AGENTS.md if a subtree needs different rules.
  - **Qodo discontinued (2026-08-16)** — free tier ended, no longer part of the review pipeline. Historical "Qodo flagged X on PR #N, confirmed false positive" notes elsewhere in this repo (e.g. `tasks/AGENTS.md`, `tasks/s01e02_findhim/AGENTS.md`) remain valid references — those findings did happen and the reasoning for dismissing them still holds — just don't expect new Qodo comments on future PRs.
  - **`.coderabbit.yaml`** (repo root, added 2026-08-16) configures CodeRabbit: `path_instructions`
    for recurring false-positive patterns (telemetry-boundary confusion, entrypoint-only
    `setup_observability()`, doc-file style nits in `tasks/**/doc/`), `knowledge_base.code_guidelines`
    reading every `AGENTS.md` directly, `auto_review.enabled: false` (matches reality — this repo is
    public but under 10 stars, so CodeRabbit never auto-reviews regardless of this setting; it's
    set explicitly so the config doesn't claim otherwise). `.claude/review-rules.md` (rules
    reconstructed from historical Qodo findings, R1-R8) and `.issues/summaries-4-human/` (triage of
    CodeRabbit's own historical findings) are the source material this config was built from.
  - **Doc edits bundled into a code PR are fine** when the doc directly describes that PR's own code (e.g. a task's `AGENTS.md` updated alongside its new `solution.py`), or when the user explicitly asked for a dedicated branch to hold a batch of doc/scaffolding work (e.g. season scaffolding).
- **Batch implementation workflow (2026-07-31):** when the user scopes a multi-part implementation as independent units (e.g. "one native tool per branch," "one feature per PR" — as with the Anthropic native-tools rollout), commit regularly during the work instead of only at the end, and give each unit its own feature branch + tests + PR, opening the PR before starting the next unit. This is the standing pattern whenever the user frames work this way; a single cohesive change still batches into one PR per the commit-routing rule above.
- **PR review follow-up (2026-08-03, revised 2026-08-16):** after opening a PR, wait 5 minutes, then check for review comments (`gh pr view <N> --json comments`). If none from CodeRabbit yet, wait another 5 minutes and check once more. If still nothing after ~10 minutes total, stop polling and tell the user directly to ping when review comments show up — don't keep silently retrying past that point. **CodeRabbit-specific:** this repo is public but under 10 stars, so CodeRabbit does NOT auto-review — `@coderabbitai review` must be triggered manually per PR, and its free-tier rate limit is tighter than it looks (two manual triggers back-to-back across two PRs hit it on 2026-08-16). Never trigger `@coderabbitai review` without the user's explicit go-ahead for that specific PR — this replaces the earlier assumption that triggering review was a safe default action.
- **Docstrings vs inline comments (2026-08-07):** these have different defaults in this repo — this narrows the base "no comments unless the WHY is non-obvious" rule to inline comments only; it does not apply to docstrings.
  - **Docstrings default ON.** Every function, method, and class gets one explaining what it does and what it's for — even a short one-liner. This is why CodeRabbit's docstring-coverage pre-merge check exists and should stay green.
  - **Inline comments default OFF**, written only when either: (a) the *why* isn't obvious from the code alone (a hidden constraint, an invariant, a workaround for a specific bug), or (b) the *benefit* of a particular *how* isn't obvious — the code does something a specific way and it's not self-evident what's gained by that choice, even when the overall goal is clear.
- **Kill switch disclosure (2026-08-08):** whenever starting anything long-running (`solve`, an agent loop, a background run), state the exact kill command in the same message — don't assume the user remembers it, and don't assume you (the agent) will still be around to kill it yourself. Guaranteed path: `bash scripts/panic.sh` (kills the whole process group, zero Python/venv dependency — works even if the environment is broken). Graceful path: `uv run run.py panic --graceful` (writes `.run/STOP`, clean `AbortRun` at the next safe checkpoint). See `core/AGENTS.md` for the full kill-switch contract.

## Child DOX Index

- `core/`: System architecture, LLM and task management base.
- `strategy/`: Project strategic documentation and workflows.
- `tasks/`: Task execution and course exercises.
- `tests/`: Project test suite and verification logic.
- `data/`: Task datasets — static inputs, fetched doc trees (`data/input/`), run outputs.
- `deploy/`: VPS deployment, systemd units, tunnel scripts.
- `.issues/`: Triage długu technicznego z dyskusji na PR-ach, podsumowania dla człowieka.
- `../misje-poboczne/`: Side missions and specific project artifacts.
