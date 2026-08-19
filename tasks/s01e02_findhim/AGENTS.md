# s01e02_findhim Module

## Purpose
Find which of several candidate suspects matches the target (name/surname
resolved via hub API access-level lookups, then narrowed by cross-referencing
each candidate's location history against power-plant coordinates). Solved —
flag `{FLG:BUSTED}` in `.flags.json`.

## Ownership
- `solution.py`: registered via `@task("s01e02", ...)`.
- Data inputs are **entirely live** — hub API calls at solve-time
  (`/api/accesslevel`, suspect location history, power-plant list) plus
  `data/main_story/people.csv` for the initial candidate roster. Nothing
  static is fetched-once-and-reused; there is no `data/input/s01e02_findhim/`.
- Power-plant coordinates are geocoded live via Nominatim (OpenStreetMap) at
  solve-time (`PowerPlant._geocode_city`), not read from a static file.

## Local Contracts
- `data/suspects.json` and `data/test_suspect_locations.json` **stay** — both
  are genuinely load-bearing (`solution.py::_load_suspects()` reads the first
  at solve-time; `test_solution.py::test_suspect_location_history_path`
  reads the second). Task-local runtime fixtures, not hub-fetched reference
  material — deliberately outside the `data/input/`/`data/output/` convention
  (see `../AGENTS.md` and `../../data/AGENTS.md`), which is specifically for
  data that might matter to a *different, later* episode. These don't qualify.
- **2026-08-05 cleanup:** removed 10 other files from `data/` —
  `FULL-power-plants-data.json`, `complete_pp_data.json`, `completed_pp_data.json`
  (empty), `power-plants-coordinates-precise.json`, `waclaw-jasinski-acces-lvl.json`,
  `waclaw-jasinski-locations.json`, and all 5 of `lokalizacje/*_locations.json`.
  None were referenced by any live code path — `test_data.py` has its own inline
  Python fixtures (`PP_LIST`, `PP_LOCATIONS_LIST`), unrelated to these JSON
  files; `lokalizacje/` only maps to `test_inspect_location_history`, which is
  `@pytest.mark.skip`ped and was never implemented. All were manual debugging
  snapshots written by the (gitignored) `tmp-quick-scripting-tests.py` scratch
  script, committed by accident, never cleaned up. Worth knowing: all three
  power-plant JSON variants also had **stale, wrong** Żarnowiec coordinates
  (~50.48/19.86, the wrong village) predating the Nominatim fix — even if one
  had still been in use, it would have been actively misleading. Recoverable
  from git history if ever needed.
- **Backlog idea, not done:** if a later episode needs Żarnowiec/PWR6132PL
  coordinates without re-running live geocoding, snapshot a *fresh, correct*
  copy into `data/output/s01e02_findhim/` — don't resurrect the removed files.

- **Znane defekty w `solution.py` — świadomie NIENAPRAWIONE, zarezerwowane na learning mode.**
  Przegląd nierozwiązanych uwag Qodo z zamkniętych PR-ów (2026-08-15, pełny zapis w
  `.issues/archive/triage-runs/closed-prs-qodo-triage.md`, sekcja B) potwierdził dwa defekty,
  które nadal żyją w kodzie. **Nie naprawiać ich mimochodem** — powód niżej.

  | Miejsce | Defekt | Osiągalny dla danych zadania? |
  |---|---|---|
  | `solution.py:39` (`GeoPoint.distance_to`) | Warunek `self.latitude and self.longitude and target.latitude and target.longitude is not None` miesza truthiness z `is None`. `is not` wiąże mocniej niż `and`, więc sprawdzenie na `None` dotyczy wyłącznie `target.longitude`; pozostałe trzy współrzędne odrzucają poprawne `0.0` (równik / południk zerowy) fałszywym `ValueError`. (→ AID-22) | **Nie** — Polska to szer. ~49–55°, dł. ~14–24°; `0.0` nie występuje. |
  | `solution.py:74-79` (`GeoPoint.is_nearest_to`) | Kandydaci kubełkowani po dokładnej wartości `float` jako kluczu `dict` (porównanie bit w bit). Docstring obiecuje „wszystkie najbliższe"; remis policzony dwiema różnymi ścieżkami arytmetycznymi mógłby rozpaść się na dwa kubełki. (→ AID-23) | **Praktycznie nie** — przy 6 miejscach po przecinku (~11 cm) dwa różne punkty albo są symetryczne względem punktu odniesienia i wychodzą bit-identycznie (`sin(dlon/2)**2` zjada znak — tak działa `point_x` w `test_is_nearest_to__parametrize`), albo różnią się o znacznie więcej niż jeden ULP. |

  Zostają nienaprawione, bo:
  1. **Zadanie jest zaliczone** — flaga `{FLG:BUSTED}`, żaden z defektów nie był na ścieżce do niej.
  2. **Nie dotykają niczego poza tym zadaniem.** `GeoPoint` nie jest importowany nigdzie poza
     `s01e02` (jedyny import spoza `solution.py` to własne `test_data.py`), nie ma go w
     `tasks/common/` i nie spełnia jego kryterium wejścia („używane w więcej niż jednym zadaniu").
     `tasks/s03/requirements/` nie zawiera geodezji — „mapa" w `s03e04`/`s03e05` to siatka 10×10,
     nie współrzędne geograficzne.
  3. **Powstały w learning mode, ręcznie.** To ostatnie zadanie napisane w przytłaczającej
     większości ręcznie, przed przejściem na efficiency mode. Ich samodzielna naprawa jest
     materiałem do nauki, a nie długiem do spłacenia przez agenta. **Termin: po powrocie do
     learning mode, czyli po zdobyciu 20 flag** — nie wcześniej, nie „przy okazji".

  Naprawione już przez autora (2026-08-15, nie wymagają dalszej pracy): `parse_location_history()`
  rzuca `ValueError` zamiast cicho zwracać `[]` dla błędnego typu; `Iterator` importowany
  z `collections.abc` zamiast prywatnego `_collections_abc`.

  Dwie martwe asercje w `test_solution.py::test_is_nearest_to__parametrize` (licznik
  `same_name_count` zerowany wewnątrz pętli po `j`, więc `<= 1` zawsze prawdziwe;
  `check_count` trywialnie spełnione) — ten sam reżim: do poprawy w learning mode.
  (→ AID-24)

## Work Guidance
- (none beyond the above — task is solved)

## Verification
- Flag confirmed by hub: `{FLG:BUSTED}`.

## Child DOX Index
- None.
