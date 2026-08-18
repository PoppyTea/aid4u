---
id: r05
severity: RETIRED
scope: "N/A"
zrodlo: "R5 (.claude/review-rules.md, Qodo 2059936) — emerytowana 2026-08-18"
---

# r05 — RETIRED: pliki niebędące kodem tylko na `main`

**Ta reguła nie jest egzekwowana.** Zachowana jako plik-marker, nie jako aktywna reguła —
patrz `strategy/rules/AGENTS.md`, sekcja "R5 — emerytowana, nie zmigrowana", dla
uzasadnienia procesu retirement.

Treść oryginalna: zmiany w `.flags.json`, plikach `*.md` i konfiguracji miały trafiać
bezpośrednio na `main`, nie na gałąź funkcjonalną — chyba że najbliższy `AGENTS.md`
zawiera jawne odstępstwo.

Powód emerytury: reguła była konsekwentnie odrzucana przy recenzji (PR #46, PR #21) —
własna adnotacja historyczna w `.claude/review-rules.md` żądała jawnej decyzji: "albo
dopisz odstępstwo do root `AGENTS.md` i usuń tę regułę, albo zostaw ją jako Opcjonalne".
Wybrano pierwsze. Intencja żyje dalej jako **commit-routing** w root `AGENTS.md`, sekcja
User Preferences: kod (`.py`) przez PR, wszystko non-code prosto na `main`, z lokalnym
odstępstwem możliwym w `AGENTS.md` dziecka.

## Jak zgłaszać
Nie zgłaszać — nieaktywna. Jeśli ktoś napotka to zachowanie flagowane przez narzędzie
zewnętrzne, odesłać do commit-routing w root `AGENTS.md`.
