---
id: r19
severity: WARNING
scope: "**"
zrodlo: "strategy/naming-conventions.md (autorytatywna)"
---

# r19 — Zgodność nazewnictwa plików

Wskaźnik, nie duplikat: `strategy/naming-conventions.md` jest jedynym źródłem prawdy dla
konwencji nazewnictwa w tym repo (kebab-case dla `.md`, snake_case dla `.py`,
UPPERCASE dla standardów roota, angielskie nazwy plików niezależnie od języka treści).
Ta reguła tylko stwierdza: `cleanup` sprawdza nowe/zmienione pliki wobec tamtego
dokumentu i jego tabeli migracyjnej — treść zasad nie jest powielana tutaj.

## Jak zgłaszać
Przez rutynę `cleanup`. Naruszenie → issue Linear `src/cleanup` + `type/hygiene`,
priorytet Niski (kosmetyka, nie ryzyko funkcjonalne) chyba że nazwa koliduje z
importem/ścieżką faktycznie używaną w kodzie.
