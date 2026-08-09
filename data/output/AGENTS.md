# data/output/

## Purpose

Data *produced* while solving a task — derived, cleaned, or geocoded, not
just a re-saved copy of what was fetched — kept because a later episode might
need it. Cross-episode continuity has already bitten us in practice (e.g.
`PWR6132PL`/Żarnowiec surfaces in `s02e02_electricity` and the `s02e05_drone`
fabuła, both after `s01e02_findhim` first resolved it). Mirror image of
`../input/` (fetched vs. produced) — see `../AGENTS.md` for the full
four-way split against `../main_story/` and `../run-history/`.

## Ownership

Owned by the course task(s) that produced each subfolder. One subfolder per
task (matching its `tasks/` folder name, e.g. `s01e02_findhim/`).

## Local Contracts

- Only save what a *different, later* task could plausibly need — not every
  intermediate scratch file from getting to the answer. If nothing here would
  survive that bar, the task doesn't get a subfolder.
- Human-readable filenames, English kebab-case, no timestamps — this is
  curated, not run history (that's `../run-history/`, automatic, gitignored).
- All hub.ag3nts.org access goes through `core.hub.client.HubClient` (see
  `../../core/AGENTS.md`) — never raw `httpx`, same rule as `../input/`.

## Work Guidance

- When a task derives something reusable (geocoded coordinates, a resolved
  identifier, a cleaned dataset), save it here explicitly at the point it's
  finalized — don't rely on `.cache/` or `../run-history/` to preserve it;
  both are disposable by design (see `../AGENTS.md`).
- Update the producing task's `AGENTS.md` (Ownership) to point at what landed
  here, same as `../input/`'s contract.

## Verification

(none yet)

## Child DOX Index

- `s02e05_drone/`: `dam_sector.json` — deterministic dam-sector detection result
  (col/row/water_fraction/all_sector_scores), produced by `map_analysis.py`
  during `solve()`. Ground truth for calibrating vision/prompts later, if
  `LLMClient` ever gains image support (see `core/AGENTS.md`) — a no-LLM
  baseline to compare against, not just a one-off answer.
