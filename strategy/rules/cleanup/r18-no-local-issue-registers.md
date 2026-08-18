---
id: r18
severity: ERROR
scope: "**/*.md"
zrodlo: "strategy/issue-tracking.md (zakaz nowych lokalnych rejestrów), migracja 2026-08-18"
---

# r18 — Zakaz nowych lokalnych rejestrów issues

Ramię egzekucyjne `strategy/issue-tracking.md`: Linear (team Aid4u) jest jedynym źródłem
prawdy dla długu technicznego tego repo. Żaden nowy plik z tabelą długu, TODO-listą czy
checklistą defektów poza Linear — powtórka pre-migracyjnego stanu (~15 rozproszonych
rejestrów, koszt zamknięcia jednej pozycji = edycja 4 plików) jest dokładnie tym, co ta
reguła ma uniemożliwić.

**Wzorzec wykrywany:** nowy `.md` z tabelą zawierającą kolumnę
`Priorytet`/`Status`/`TODO` opisującą stan pojedynczych zadań/defektów, poza dozwolonymi
wyjątkami:
- 10 plików `.issues.md` — generowane z API Linear, nie ręcznie edytowane pointer'y.
- `tasks/sXX/requirements/season.md` i `tool-inventory.md` — żywe checklisty sezonu
  kursowego, nie rejestry długu (rozróżnienie w `strategy/issue-tracking.md`, Ownership).
- Inline `(→ AID-XXX)` w istniejącym dokumencie — kotwica, nie tabela.

## Jak zgłaszać
Wyłącznie przez rutynę `cleanup`. `ERROR` — nienegocjowalne, ale zgłoszenie jest
informacyjne (audyt jest read-only wobec kodu/treści, nie usuwa pliku sam). Issue Linear
`src/cleanup` + `type/hygiene`, priorytet Wysoki (żywi z powrotem problem, który migracja
miała zamknąć).
