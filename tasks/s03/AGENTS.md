# tasks/s03/

## Purpose
Pierwszy w tym repo folder grupujący coś na poziomie SEZONU pod `tasks/` (dotąd
płasko: `tasks/sXXeYY_nazwa/`). Istnieje wyłącznie dla `requirements/` — przeglądu
gotowości i checklist przed startem sezonu 3. Procedura ogólna, sezonoagnostyczna,
żyje w `strategy/season-transition.md`; ten folder trzyma konkretną instancję dla S03.

## Ownership
- `requirements/`: raport gotowości + checklisty per-zadanie dla sezonu 3.

## Local Contracts
- **Foldery poszczególnych zadań (`s03e01_evaluation/` itd.) NIE trafiają tutaj** —
  zostają płaskie pod `tasks/`, tak jak `s01e0X_*`/`s02e0X_*`. Ten folder to
  wyłącznie materiał przygotowawczy, nie kontener na implementacje.
- ⚠️ **Ani `tasks/s03/`, ani `tasks/s03/requirements/` nie mogą dostać
  `__init__.py`.** `tasks/__init__.py` robi auto-import przez
  `pkgutil.iter_modules()` nad każdym pakietem bezpośrednio w `tasks/` — dodanie
  `__init__.py` zamieniłoby folder dokumentacyjny w pusty/błędny "moduł zadania".

## Work Guidance
(brak — szczegóły w `requirements/AGENTS.md`)

## Verification
(none yet)

## Child DOX Index
- `requirements/`: raport gotowości na S03 + checklisty per-zadanie.
