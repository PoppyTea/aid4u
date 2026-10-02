# Reguły recenzji i audytu (DOX)

## Purpose
Mechanika formatu reguł tego repo — jedna reguła, jeden plik — plus powód, dla którego
ten folder istnieje jako `AGENTS.md`, nie jako zwykły `.md`: `.coderabbit.yaml` czyta
`knowledge_base.code_guidelines` z `filePatterns: ["**/AGENTS.md"]`. CodeRabbit **nigdy**
nie czytał `.claude/review-rules.md` (stary dom R1-R8, usunięty przy tej migracji) — to
pierwszy raz, kiedy reguły tego repo stają się widoczne dla automatycznego recenzenta,
nie tylko dla agenta w sesji lokalnej.

## Ownership
Jedna reguła = jeden plik `rNN-slug.md`. Numeracja **globalna i ciągła**, kontynuacja
starego R1-R8 — nowe reguły migrowane zaczynają od `r09`. Frontmatter obowiązkowy w
każdym pliku reguły:

```yaml
---
id: rNN
severity: ERROR | WARNING | RECOMMENDATION
scope: <path glob(y), gdzie reguła obowiązuje>
zrodlo: <skąd reguła pochodzi — stary numer Qodo, PR, audyt>
---
```

### Severity — egzekwowanie
Tabela przeniesiona z `.claude/review-rules.md` (kontrakt wyjściowy dawnego skilla
`qodo-get-rules`, zachowany dla ciągłości semantyki egzekwowania mimo że Qodo jako
narzędzie jest discontinued od 2026-08-16):

| Severity | Egzekwowanie przy pisaniu kodu | Pasmo w recenzji PR |
|---|---|---|
| `ERROR` | nienegocjowalne; przy zastosowaniu dopisz komentarz dokumentujący zgodność | `Action_required` |
| `WARNING` | domyślnie stosuj; pominięcie wymaga jednozdaniowego uzasadnienia | `Review_recommended` |
| `RECOMMENDATION` | rozważ, gdy pasuje | `Optional` |

Sentinel dodatkowy: `severity: RETIRED` oznacza plik-marker zachowany dla śladu
historycznego, wyłączony z egzekwowania i z digestu ERROR niżej — patrz
`common/r05-retired.md`.

### Podfoldery
- `common/` — reguły egzekwowane przez **każdą** rutynę czytającą kod (pisanie kodu,
  `pr-review`, `contract-audit`).
- `pr-review/` — reguły znaczące tylko przy patrzeniu na diff PR-a (wymagają kontekstu
  "co się zmieniło", nie mają sensu jako skan całego repo).
- `contract-audit/` — meta-reguły audytu całorepo: rozjazd propagacji poprawek i filtr
  cichych awarii, zdestylowane z `qudo-skills-alt/prompty-scheduled-tasks.md` §D.
- `cleanup/` — reguły higieny repo: zakaz lokalnych rejestrów issues, zgodność
  nazewnictwa, pliki nie na miejscu, świeżość `.issues.md`.
- `coderabbit-ingest/` — polityka triage'u wyników CodeRabbit: remap severity → nasz
  priorytet, znane fałszywe pozytywy. **Referencja**, nie duplikat: `.coderabbit.yaml`
  (`path_instructions`) zostaje autorytatywnym źródłem treści tych wzorców.

## Local Contracts

### Digest reguł ERROR — to czyta CodeRabbit
Reguły `ERROR` w pełnej treści (nie skrót) tego repo. Pozostałe severity żyją tylko w
swoich plikach `rNN-*.md` — CodeRabbit dostaje z tego digestu sygnał, których naruszeń
nie negocjować.

| id | Reguła (jedno zdanie) | Dowód `plik:linia` |
|---|---|---|
| `r13` | Zadanie wołające `hub.submit()` wewnątrz `solve()` musi nadpisać `_submit()` albo `run()`, inaczej `BaseTask.run()` wysyła flagę drugi raz. | `tasks/s02e03_failure/solution.py:223,269` |
| `r14` | `except httpx.HTTPStatusError` musi sprawdzać konkretny udokumentowany kod, resztę re-raise'ować; `response.json()` na ścieżce błędu zawsze w `try/except ValueError`. | `tasks/s02e03_failure/solution.py:270-271` |
| `r18` | Zakaz nowych lokalnych rejestrów długu/TODO poza Linear — jedno źródło prawdy, patrz `strategy/issue-tracking.md`. | wzorzec: nowy plik `.md` z tabelą kolumn Priorytet/Status poza `.issues.md` |

### R5 — emerytowana, nie zmigrowana
Stare R5 ("pliki non-code tylko na `main`") **nie ma aktywnego slotu reguły** — jedyny
ślad to plik-marker `common/r05-retired.md` (`severity: RETIRED`, poza egzekwowaniem
i poza digestem ERROR wyżej). Była konsekwentnie odrzucana przez recenzenta (PR #46, PR #21) — trzymanie reguły
ignorowanej systematycznie uczy ignorowania całej sekcji (własna adnotacja R5 tego
żądała). Intencja przeżyła jako commit-routing w root `AGENTS.md` (User Preferences):
zmiany non-code idą prosto na `main`, kod przez PR — bez sztywnego "zawsze main dla
markdown", z lokalnym odstępstwem dozwolonym w `AGENTS.md` dziecka.

## Work Guidance
- **Dodanie reguły:** nowy plik w odpowiednim podfolderze, kolejny numer globalny,
  frontmatter komplet, treść + `## Jak zgłaszać` (odwołanie do labeli Linear
  `type/*`/`src/*` z `strategy/issue-tracking.md`). Jeśli `severity: ERROR` — dopisz wiersz
  do digestu wyżej.
- **Retirement reguły** (patrz też `strategy/quality-control.md`): reguła stale i
  świadomie odrzucana przy recenzji nie zostaje jako martwy `ERROR`/`WARNING`. Dwie
  opcje: skodyfikować jako jawny wyjątek gdzie indziej (jak R5 → commit-routing) i usunąć
  plik reguły, albo obniżyć `severity` do `RECOMMENDATION` i zostawić plik z adnotacją
  czemu spadła.
- **Propozycje niezaakceptowane:** kandydaci z web recon czy z obserwacji lądują w
  `proposed-rules-*.md` w tym folderze, **nigdy** bezpośrednio jako `rNN` — auto-adopcja jest
  zakazana, potrzebna jest jawna akceptacja usera.

## Verification
(brak — brak jeszcze automatycznego lintu formatu frontmatter)

## Child DOX Index
- `./common/` - Reguły dla każdej rutyny czytającej kod (r09, r12-r15; + r05-retired.md,
  marker historyczny poza egzekwowaniem).
- `./pr-review/` - Reguły znaczące tylko przy diffie PR-a (r10, r11).
- `./contract-audit/` - Meta-reguły audytu całorepo (r16, r17).
- `./cleanup/` - Reguły higieny repo i egzekwowania Linear-jako-jedynego-rejestru (r18-r20).
- `./coderabbit-ingest/` - Polityka triage'u CodeRabbit → Linear (r21, r22).
- `proposed-rules-2026-08-18.md` - Kwarantanna propozycji reguł czekających na akceptację;
  **nie jest egzekwowana** — nic tu nie obowiązuje, dopóki nie trafi do podfolderu jako `rNN`.
