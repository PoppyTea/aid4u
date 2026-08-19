---
id: r11
severity: RECOMMENDATION
scope: "core/**/*.py, tasks/**/*.py"
zrodlo: "R3 (.claude/review-rules.md, Qodo 2603753)"
---

# r11 — Docstringi publicznych symboli

Każda publiczna funkcja, metoda i klasa (nazwa nie zaczyna się od `_`) ma niepusty
docstring jako pierwszą instrukcję. Obejmuje klasy testowe (`TestXxx`) i nadpisania
metod bazowych (`solve`, `fetch_data`).

> **Uwaga z historii:** przy klasach pytest dawne narzędzie (Qodo) samo obniżało tę
> regułę do "umiarkowana". Jeśli testy mają być zwolnione z wymogu — dopisz tu jawny
> wyjątek zamiast po cichu ignorować zgłoszenia.

Zgodne z `AGENTS.md` root, User Preferences: "Docstringi default ON" — ta reguła jest
egzekwowaniem tamtej decyzji na poziomie recenzji PR-a.

## Jak zgłaszać
Komentarz na PR przy symbolu bez docstringa. Nie zakłada issue w Linear — poziom
`RECOMMENDATION`, drobna poprawka w miejscu.
