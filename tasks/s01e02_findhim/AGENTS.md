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

## Work Guidance
- (none beyond the above — task is solved)

## Verification
- Flag confirmed by hub: `{FLG:BUSTED}`.

## Child DOX Index
- None.
