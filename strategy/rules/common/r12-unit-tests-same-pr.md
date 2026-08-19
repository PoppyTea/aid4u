---
id: r12
severity: WARNING
scope: "core/**/*.py, tasks/**/*.py"
zrodlo: "R4 (.claude/review-rules.md, Qodo 1518481)"
---

# r12 — Testy jednostkowe dla nowego kodu produkcyjnego

Nowy lub zmodyfikowany kod produkcyjny wymaga testów jednostkowych w tym samym PR.

Dla zadań deterministycznych (bez LLM w pętli) minimum to test sekwencji wywołań hubu
przez stub/fake — że `solve()` wykonuje kroki protokołu w oczekiwanej kolejności i
zwraca właściwy payload.

Testy pokrywające zmiany w `core/` **nie** zaspokajają tej reguły dla nowego modułu w
`tasks/`.

**Wyjątek udokumentowany w `.coderabbit.yaml`:** `tasks/**/solution.py` — brak testów
jednostkowych nie jest tam problemem z rozmysłem (`tasks/AGENTS.md`), weryfikacja przez
realny hub liczy się bardziej. Ta reguła obowiązuje mimo to dla `core/` i dla logiki, na
której faktycznie zależy poprawność (nie samego rytuału `test_solution.py`).

## Jak zgłaszać
Komentarz na PR wskazujący brakującą ścieżkę testową, jeśli naruszenie znalezione poza
PR-em (np. `contract-audit`) — issue Linear `type/tech-debt`.
