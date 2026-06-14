# AID4U Project Memory

## Projekt
AI_Devs 4 — Python workspace do rozwiązywania zadań kursu agentami AI.
Kurs: 5 tygodni, ~25 zadań. Start: 2026-03-09.

## Architektura (zatwierdzona 2026-03-11)
**Layered ReAct Single-Agent** → ADR-001
- `core/` settings + schemas | `providers/` llm + hub | `agents/` base + supervisor
- `tasks/sXXeYY/` tools + schemas + task | `tui/` app | `main.py`
- BaseTask Protocol w `tasks/base.py` — interfejs dla TUI i przyszłego Supervisora
- Ewolucja: W3+ supervisor.py aktywny, W3+ RAG

## Observability (zatwierdzona 2026-03-11)
- **Langfuse** (cloud.langfuse.com) = primary: tokeny, koszty, traces
- **Logfire** = dev: spans, debugging
- Token counting: `result.usage().total_tokens` po każdym Agent.run()

## CLAUDE.md filozofia
- Minimal: drogowskaz, nie encyklopedia
- Root CLAUDE.md: język + profil + mapa projektu (~20 linii)
- Workspace CLAUDE.md: entry + 4 zasady krytyczne (~24 linie)
- Szczegóły → vault: `01_memory/02_long_term/AI_Devs_4/architecture/`

## Dokumentacja w vault
`AI_Devs_4/architecture/`:
- PROJECT.md, GLOSSARY.md, DOC-STANDARD.md
- ADR-001 (architektura), ADR-002 (observability)
- PROMPT_refactor-layered-arch.md ← do użycia w sesji refaktoryzacji

## Stan kodu (2026-03-11)
- s01e01 rozwiązane (monolith w tasks/s01e01_app.py) — zadanie ukończone
- Refaktoryzacja do Layered arch: NIE ZROBIONA → prompt gotowy w vault

## Preferencje Lis
- Polski, krótko, kod przed wyjaśnieniami
- Gentle Momentum: jeden temat na raz
- uv run, uv add | Textual @work | tenacity na sieci
