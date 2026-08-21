# tasks/s04/

## Purpose
Folder grupujący na poziomie SEZONU, wzorowany na `tasks/s03/`. Istnieje wyłącznie dla
`requirements/` — rekonesansu przed końcówką kursu.

⚠️ **Zakres jest szerszy niż nazwa.** `requirements/` obejmuje **S04 i S05 razem**, bo do
certyfikatu brakuje 5 flag, a zostało 10 zadań — wybór jest jeden, przekrojowy przez oba
sezony, i rozbicie go na `s04/` + `s05/` rozerwałoby ranking na pół. Jeśli kiedyś powstanie
`tasks/s05/`, będzie na implementacje S05, nie na drugi rekonesans.

## Ownership
- `requirements/`: ranking 10 pozostałych zadań, wybrana piątka, kolejność ataku,
  materiał źródłowy.

## Local Contracts
- **Foldery poszczególnych zadań (`s04e03_domatowo/` itd.) NIE trafiają tutaj** — zostają
  płaskie pod `tasks/`, tak jak `s01e0X_*`/`s02e0X_*`/`s03e0X_*`.
- ⚠️ **Ani `tasks/s04/`, ani `tasks/s04/requirements/` nie mogą dostać `__init__.py`.**
  `tasks/__init__.py` robi auto-import przez `pkgutil.iter_modules()` nad każdym pakietem
  bezpośrednio w `tasks/` — dodanie `__init__.py` zamieniłoby folder dokumentacyjny
  w pusty/błędny „moduł zadania".

## Work Guidance
(brak — szczegóły w `requirements/AGENTS.md`)

## Verification
(none yet)

## Child DOX Index
- `requirements/`: rekonesans S04+S05, ranking i wybrana piątka.
