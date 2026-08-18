# Śledzenie issues — Linear

## Purpose
Linear (team **Aid4u**, key `AID`, free tier) jest **jedynym źródłem prawdy** dla długu
technicznego tego repo. Decyzja zapadła 2026-08-18: przed migracją dług był rozproszony po
~15 rejestrach — `aid4u/.issues/` (3 kolidujące namespace'y ID), zapomniany drugi
`.issues/` w roocie repo, tabele w `tool-inventory.md`/`season.md`, checklisty
`tasks/s03/requirements/`, wpisy w różnych `AGENTS.md`, stale doki. Koszt zamknięcia
**jednej** pozycji był edycją 4 plików, bo nikt nie wiedział z góry, w którym rejestrze
dana pozycja żyje. Linear zastępuje wszystkie te rejestry jako miejsce zapisu i stanu;
ten dokument opisuje cykl życia issue w nowym układzie, nie samą migrację (patrz dziennik
migracji w `.issues/AGENTS.md` dla historii jednorazowej).

## Ownership
Granice między Linear a sąsiednimi artefaktami — każdy fakt ma jeden dom:

| Typ faktu | Dom | Nie w Linear, bo |
|---|---|---|
| Dług techniczny / bug / hygiene | Linear (`AID-XXX`) | to jest dokładnie ten przypadek |
| Decyzja architektoniczna bez terminu | `strategy/open-decisions.md` | pytanie do rozstrzygnięcia, nie zadanie do wykonania |
| Checklista sezonu kursowego | `tasks/sXX/requirements/` (np. `season.md`) | żywy plan gry, nie rejestr defektów |
| Reguła recenzji kodu | `strategy/rules/` | kontrakt trwały, nie zdarzenie do zamknięcia |

Lokalne artefakty, które **zostają** mimo Linear:
- **10 plików `.issues.md`** (per moduł: `core/`, `tests/`, `data/`, `strategy/`, `.claude/`
  i pięć `tasks/sXXeYY_*/`) — generowane z API Linear przez rutynę `cleanup`, tabela
  `AID | Tytuł | Priorytet | Link`. Nie edytować ręcznie — czysty pointer, nie rejestr.
- **`.issues/summaries-4-human/`** — jedyna rzecz, której Linear nie zastępuje: narracyjne
  podsumowanie triage'u pisane dla człowieka (kontekst PR-a, kompromisy, plan wdrożenia).
  Tu pisze rutyna `review-ingest` i skill `pr-review-triage`; kontrakt w `.issues/AGENTS.md`.

## Local Contracts

### Cykl życia
`Triage → Todo → In Progress → Done | Odłożone | Canceled`. `Odłożone` to własny stan
(nie natywny Linear) dla pozycji świadomie wstrzymanych — patrz Work Guidance.
`Canceled` dla pozycji odrzuconych (nie duplikat, nie odłożone — po prostu nie robimy);
rekord zostaje, bo dedup przeszukuje **wszystkie** stany, nie tylko otwarte.

### Priorytety — własna ocena, nigdy severity narzędzia
| Nasza skala | Linear native |
|---|---|
| Wysoki | High |
| Średni | Medium |
| Niski | Low |
| Nieznany | No priority |

`Urgent` zarezerwowany dla jednej klasy: wyciek sekretu. Zasada przeniesiona z dawnego
`.issues/AGENTS.md`: **nie kopiuj bezmyślnie** severity CodeRabbit (Major/Minor/Nit) ani
dawnego Qodo (ERROR/WARNING) na priorytet — oceń realne ryzyko **w tym repo** (zamknięty,
zaliczony epizod kontra żywa infrastruktura używana co sesję). Sekcja opisu issue
`## Uzasadnienie priorytetu` jest obowiązkowa zawsze, nie tylko gdy priorytet jest
nieoczywisty — brak realnego uzasadnienia = `Nieznany`, nie zgadywanie.

### Taksonomia labeli
Grupy (`parentId`, max 1 label per issue per grupa — celowo, dyscyplinuje wybór):
`area/*` (core, tasks, tests, docs, data, observability, deploy, tooling, strategy),
`type/*` (bug, tech-debt, feature, docs, hygiene), `src/*` (coderabbit, qodo,
contract-audit, cleanup, deprecation-watch, manual, migration-2026-08). Standalone:
`security`, `learning-mode` (oznacza zakaz naprawy — epizod zaliczony, kod zamrożony
celowo), `needs-verification`.

`gate/*` (`pre-e02`, `pre-e05`, `s04`, …) ma semantykę **warunku, nie daty** — "napraw
zanim zaczniesz e02", nie "napraw do 30.08". Termin kalendarzowy idzie w natywne
`dueDate` Linear, nie w label.

### Dedup-first
Przed założeniem jakiegokolwiek issue: **szukaj w Linear po wszystkich stanach**
(Triage/Todo/In Progress/Done/Odłożone/Canceled), nie tylko po otwartych — pozycja
odrzucona wcześniej z powodem w komentarzu nie powinna wrócić bez nowego argumentu.
Markery dedupu wpisywane w opis issue:

| Marker | Znaczenie |
|---|---|
| `gh-pr:<NUM>#<id>` | wątek recenzji na konkretnym PR (id komentarza/review) |
| `odcisk:<ścieżka::reguła::symbol>` | naruszenie kontraktu znalezione przez `contract-audit` |
| `migracja:<stare-ID>` | pozycja przeniesiona ze starego rejestru plikowego |

**`Fixes AID-XXX` jest obowiązkowe** w opisie każdego PR-a, który naprawia issue — magic
word GitHub-Linear integration automatycznie przestawia stan na Done po merge.

### Zakaz nowych lokalnych rejestrów
Żaden nowy plik z tabelą długu, TODO-listą czy checklistą defektów poza Linear. Rutyna
`cleanup` (patrz `strategy/quality-control.md`) wykrywa naruszenia tej reguły —
egzekwowana przez `strategy/rules/cleanup/r18-no-local-issue-registers.md`.

## Work Guidance
- **Zgłaszanie:** dedup-first (wyżej) → `issueCreate` w Triage z opisem: Dowód
  (`plik:linia`), Jak zawiedzie, Uzasadnienie priorytetu, Źródło. Automatyczne rutyny
  tworzą tickety same (patrz lejek niżej); ręczne zgłoszenie jest wyjątkiem, nie normą.
- **Zamykanie:** merge PR-a z `Fixes AID-XXX` w opisie → auto-Done. Ręczne przejście do
  Done tylko gdy naprawa nie przechodzi przez PR (np. config zmieniony bezpośrednio).
- **Odłożone** wymaga **jednego z trzech**: label `gate/*`, natywny `dueDate`, albo
  jawny warunek zapisany w opisie ("wróć, gdy zacznie się S04"). Odłożenie bez żadnego
  z tych trzech jest w praktyce Canceled z lepszym PR-em.
- **Lejek naturalnie pojawiających się diagnoz** — każde źródło ma jedną, deterministyczną
  ścieżkę do Linear, żeby nic nie kończyło w piątym rejestrze:
  - CodeRabbit → rutyna `review-ingest` → Triage.
  - Raporty rutyn (`contract-audit`, `cleanup`) → **same tworzą tickety** przez API, nie
    tylko raport do przeczytania.
  - TODO/tabelka długu znaleziona w dokumentacji → eliminować **u źródła** (usuń tabelę,
    załóż issue), zostaw najwyżej inline `(→ AID-XXX)` jako kotwicę, nigdy pełną tabelę.

## Verification
- Rutyna `cleanup` sprawdza świeżość wszystkich 10 plików `.issues.md` (re-query Linear +
  diff) i skanuje repo pod kątem nowych plików pasujących do wzorca lokalnego rejestru
  (tabela z kolumną "Priorytet"/"Status", nagłówek TODO poza `.issues.md`).
- Spot-check ręczny — GraphQL, wzorzec zapytania:
  ```graphql
  query { issues(filter: { team: { key: { eq: "AID" } } }) {
    nodes { identifier title state { name } priority } } }
  ```

## Child DOX Index
- None.
