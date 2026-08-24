---
id: r22
severity: RECOMMENDATION
scope: "N/A — polityka triage'u, nie kod"
zrodlo: ".coderabbit.yaml (path_instructions, autorytatywny)"
---

# r22 — Znane fałszywe pozytywy CodeRabbit

**Referencja, nie duplikat.** `.coderabbit.yaml` (`reviews.path_instructions`, root repo)
jest autorytatywnym źródłem treści tych wzorców — ten plik tylko nazywa je, żeby
`review-ingest` wiedziała, których kategorii szukać przy triage'u, bez kopiowania
sformułowań yaml-a (który i tak jest podawany CodeRabbitowi bezpośrednio).

Wzorce znane jako niski priorytet / zwykle false-positive w tym repo (patrz
`.coderabbit.yaml` dla dokładnej instrukcji per ścieżka):

- `core/llm/client.py` — pomylenie granicy telemetrii: sugestie routowania wywołań
  Langfuse/Logfire przez `LLMClient`, mimo że to świadomie osobna warstwa.
- `core/observability/**` — sugestie wołania `setup_observability()` w modułach
  bibliotecznych, mimo że entrypoint (`run.py`) już to robi (funkcja idempotentna).
- `tasks/**/doc/*.md` — nitpicki stylu/markdownlint na materiałach referencyjnych kursu
  (transkrypcje, kopie treści zadania) — nieużywane w runtime, niski priorytet z
  wyjątkiem realnych sekretów w treści.
- `tasks/*/AGENTS.md` — sugestie usunięcia nagłówka statusu epizodu („Rozwiązane (data) —
  flaga, koszt") jako „wpisu dziennikowego". To wymagany element kontraktu tych plików,
  nienoszony przez jeden plik, tylko przez wszystkie rozwiązane epizody; koszt i liczba
  podejść karmią planowanie sezonu. Dodane 2026-08-24 po PR #81.

## Jak zgłaszać
Egzekwowane przez `review-ingest`: finding CodeRabbit pasujący do jednego z wzorców
wyżej jest downgradowany (severity niżej) albo pomijany przy tworzeniu ticketu w Linear,
z adnotacją w opisie `known-fp: <wzorzec>` dla śladu, czemu nie stał się osobnym issue.
