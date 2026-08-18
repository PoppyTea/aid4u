---
id: r13
severity: ERROR
scope: "tasks/**/solution.py, core/tasks/base.py"
zrodlo: "R6 (.claude/review-rules.md, 'nowa — z obserwacji')"
---

# r13 — Kontrakt pojedynczej submisji

`BaseTask.run()` zawsze wykonuje `_submit()` po `solve()`. Zadanie, które woła
`hub.submit()` **wewnątrz** `solve()` (pętla feedbacku, protokół wieloetapowy), musi:

- nadpisać `_submit()` tak, by zwracał flagę przechwyconą w `solve()` bez ponownego
  wywołania hubu, **albo**
- nadpisać `run()`, pomijając bazowy krok submisji.

Dodatkowo: każde bezpośrednie `hub.submit()` w kodzie zadania musi respektować
`self.dry_run` — `BaseTask._submit()` jest jedynym miejscem, które to egzekwuje, więc
obejście go łamie semantykę `--dry-run`.

> **Uwaga z historii:** naruszenie było potwierdzone w kodzie 14.08.2026 —
> `tasks/s02e03_failure/solution.py` ma `solve()` (223) i `hub.submit()` (269) wprost, bez
> `_submit()`/`run()` — `BaseTask.run()` wysyłał flagę drugi raz. To była uwaga #3 z PR
> #56, nienaprawiona; poprawka z PR #57 była task-lokalna (`_submit()` w `MailboxTask`) i
> z definicji nie objęła `FailureTask`. Status bieżący nieznany tej migracji — do
> zweryfikowania i, jeśli wciąż aktualne, założenia w Linear przez `contract-audit`.

## Jak zgłaszać
`ERROR` — nienegocjowalne. PR: `BLOCKER`. Poza PR-em (audyt całorepo): issue Linear
`type/bug` + `area/tasks`, priorytet Wysoki (podwójna submisja może spalić próbę na
hubie).
