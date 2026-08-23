# Issues / Triage

## Purpose
Nie jest już bazą długu technicznego — Linear (team **Aid4u**, key `AID`) jest jedynym
źródłem prawdy, patrz `strategy/issue-tracking.md`. Ten folder zostaje z dwóch powodów:
historyczne archiwum dawnych przebiegów triage'u sprzed migracji (2026-08-18) i dom
narracyjnych podsumowań recenzji PR-ów, których Linear nie zastępuje.

## Ownership
- `summaries-4-human/`: podsumowania pisane dla człowieka (kontekst, kompromisy, plan
  wdrożenia) — nie dla agenta, Linear trzyma tickety do wykonania. Dwa rodzaje wpisów:
  - **triage PR-a** — piszą rutyna `review-ingest` i skill `pr-review-triage`, jeden plik
    na przebieg, `<NUM>-review.md`;
  - **notatka sesyjna** — `RRRR-MM-DD-<temat>.md`, gdy jedna sesja dotknęła wielu rzeczy
    naraz i część świadomie odłożyła. Zapisuje **to, czego Linear nie trzyma**: co
    odrzucono i na jakiej podstawie, czego nie robić, jakie rozróżnienie pojęciowe z tego
    wyszło. Nigdy lista zadań do wykonania — to byłby lokalny rejestr zakazany przez
    `strategy/rules/cleanup/r18-no-local-issue-registers.md`.
- `archive/`:
  - `triage-runs/`: dawne zbiorcze przebiegi triage'u (Qodo/CodeRabbit, sprzed migracji
    do Linear) — każdy z bannerem mapującym stare-ID → `AID-XXX`, treść pod bannerem
    nietknięta jako ślad historyczny.
  - `legacy-root-issues/`: absorpcja zapomnianego drugiego rejestru `.issues/` z rootu
    `00_aid4u/` (poza tym repo git) — pozycje pokryte przez `AID-5`/`AID-6`.

## Local Contracts
Jedna reguła behawioralna: **dedup = szukaj w Linear (wszystkie stany), nigdy w plikach
tego folderu.** Pełny kontrakt dedup-first, markery, cykl życia issue — patrz
`strategy/issue-tracking.md`.

## Work Guidance
(brak — patrz `strategy/issue-tracking.md` Work Guidance dla lejka diagnoz)

## Verification
(brak lokalnej — patrz `strategy/issue-tracking.md` Verification)

## Child DOX Index
- None.
