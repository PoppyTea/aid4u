---
id: r09
severity: WARNING
scope: "core/**, tasks/**, **/AGENTS.md"
zrodlo: "R1 (.claude/review-rules.md, Qodo 1490944)"
---

# r09 — Dokumentacja kontraktów w AGENTS.md

Zmiana zachowania lub kontraktu komponentu wymaga aktualizacji **najbliższego**
`AGENTS.md` w kaskadzie (root → `core/` → `tasks/` → `tasks/sXXeYY_*/`).

Wyzwalacze: nowy tryb błędu, nowe zachowanie retry/sleep, zmiana sygnatury publicznej
metody, zmiana semantyki zwracanej wartości.

## Jak zgłaszać
PR review lokalny (`pr-review`) lub CodeRabbit: komentarz przy pliku kodu wskazujący,
który `AGENTS.md` w kaskadzie powinien się zmienić, a się nie zmienił. Jeśli naruszenie
jest odkryte poza kontekstem PR-a (np. przez `contract-audit`) — issue w Linear z labelem
`type/docs` + `area/*` właściwym dla dotkniętego modułu.
