---
id: r20
severity: WARNING
scope: "**/.issues.md"
zrodlo: "strategy/issue-tracking.md (Ownership, artefakty lokalne), migracja 2026-08-18"
---

# r20 — Świeżość plików `.issues.md`

10 plików `.issues.md` (`core/`, `tests/`, `data/`, `strategy/`, `.claude/`, i pięć
`tasks/sXXeYY_*/`) muszą odzwierciedlać bieżący stan Linear — są generowanym pointer'em
(tabela `AID | Tytuł | Priorytet | Link`), nie ręcznie utrzymywanym rejestrem.

**Sprawdzenie:** re-query Linear po `area/*` odpowiadającym modułowi → diff z zawartością
pliku. Rozjazd = albo plik nie był regenerowany po zmianie stanu w Linear, albo ktoś
edytował go ręcznie (co samo w sobie jest naruszeniem — plik niesie nagłówek "generowany,
nie edytuj ręcznie").

## Jak zgłaszać
Przez rutynę `cleanup` — naprawa jest automatyczna (regeneracja z API), więc zwykle nie
potrzebuje osobnego issue w Linear; jeśli rozjazd wraca uporczywie (regeneracja nie
utrzymuje się), zgłoś jako `src/cleanup` + `type/tech-debt` — sygnał, że coś w samej
rutynie regeneracji jest zepsute.
