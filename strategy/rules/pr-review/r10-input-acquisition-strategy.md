---
id: r10
severity: WARNING
scope: "tasks/**/AGENTS.md"
zrodlo: "R2 (.claude/review-rules.md, Qodo 2519038)"
---

# r10 — Strategia pozyskiwania danych wejściowych

Sekcja `Ownership` w `AGENTS.md` zadania musi opisywać, **zanim** `solve()` zostanie
zaimplementowane:

- źródło i typ wejścia (endpoint, nazwa pliku, format),
- mechanizm uwierzytelnienia,
- zmienność danych (czy snapshot jest stabilny między sesjami / apikey),
- czy i jak używane jest cache'owanie.

Naruszenie: implementacja `solve()` obecna, a którykolwiek z czterech punktów
nieudokumentowany. Ma sens tylko przy patrzeniu na diff nowego zadania — stąd
`pr-review`, nie `common`.

## Jak zgłaszać
Komentarz na PR wprowadzającym `solve()` nowego zadania, wskazujący brakujący punkt.
