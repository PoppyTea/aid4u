---
id: r16
severity: WARNING
scope: "core/**, tasks/**"
zrodlo: "qudo-skills-alt/prompty-scheduled-tasks.md §D (contract-audit)"
---

# r16 — Rozjazdy propagacji poprawek

Meta-reguła audytu całorepo — cel, dla którego `contract-audit` w ogóle istnieje.
`pr-review` widzi tylko diff jednego PR-a; nie zauważy, że poprawka przyjęta w jednym
zadaniu nie została zastosowana w trzech innych, bo tamte pliki się w tym PR-ze nie
zmieniają. Zmerge'owany kod przestaje być oglądany przez kogokolwiek — dokładnie tak
powstały r13/r14/r15 (dawne R6-R8): jedna naprawa lokalna, reszta repo nietknięta.

**Heurystyka:** znajdź wzorzec obronny obecny w co najmniej jednym miejscu, a nieobecny
w innym, gdzie miałby zastosowanie. Przykłady kształtu (nie wyczerpują tematu — szukaj
analogicznych):

- jedna metoda w klasie ma `reraise=True`, siostrzane nie mają (r15);
- jedno zadanie nadpisuje `_submit()`, inne wołające hub w `solve()` — nie (r13);
- jedno miejsce sprawdza `status_code` przed potraktowaniem odpowiedzi jako feedback,
  inne łapie wszystko (r14);
- jedno miejsce respektuje `self.dry_run`, inne woła hub bezwarunkowo.

Dla każdego znalezionego rozjazdu audyt podaje **oba** miejsca: to z zabezpieczeniem i to
bez — kopiowanie własnego, przyjętego rozwiązania jest tańsze niż wymyślanie nowego.

## Jak zgłaszać
Wyłącznie przez rutynę `contract-audit`, po przejściu filtra r17. Issue Linear
`src/contract-audit` + `area/*` właściwy, opis z markerem `odcisk:<ścieżka::reguła::symbol>`.
