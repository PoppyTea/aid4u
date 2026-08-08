"""
S02E05 — drone

Przeprogramowuje uzbrojonego drona: misja jest ZADEKLAROWANA jako atak na elektrownię
Żarnowiec (`PWR6132PL`), ale faktyczny ładunek spada na sektor z tamą — dokładnie tak
jak każe fabuła (`doc/fabula.md`). Sektor tamy jest wykrywany deterministycznie z mapy
(`map_analysis.py`, czerwone linie siatki + podbita intensywność wody), bez LLM/vision —
`LLMClient` w tym repo nie ma dziś żadnego wsparcia dla obrazów (patrz `core/AGENTS.md`).

Pełny kontrakt API drona (`data/input/s02e05_drone/drone.html`) jest znany z góry —
w odróżnieniu od `s02e04_mailbox`, gdzie protokół trzeba było odkrywać na żywo, tu
dokumentacja jest jawna i statyczna, więc sekwencja instrukcji jest budowana wprost,
bez pętli agentowej. Jedyna niepewność to czy hub zaakceptuje sekwencję za pierwszym
razem — stąd ograniczona pętla feedbacku (patrz `solve()`), nie pełny agent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import logfire

from core.net import expect_binary
from core.tasks import BaseTask, task
from tasks.s02e05_drone.map_analysis import DamSectorResult, detect_dam_sector

HUB_TASK_NAME = "drone"
PLANT_ID = "PWR6132PL"

_ALTITUDE_M = 50
_ENGINE_POWER_PERCENT = 100
_MAX_ATTEMPTS = 2  # sektor jest wysoko pewny (patrz map_analysis) — dodatkowe próby to
# tylko czyszczenie stanu (hardReset), nie zgadywanie innego sektora "na chybił trafił".

_DAM_SECTOR_ARTIFACT = Path("data/output/s02e05_drone/dam_sector.json")


def _build_instructions(*, col: int, row: int) -> list[str]:
    """
    Buduje sekwencję instrukcji wg kontraktu z drone.html:
    - `hardReset` na starcie — config drona jest trzymany po stronie serwera i
      kumuluje się między próbami (potwierdzone w komentarzach kursu).
    - `setDestinationObject(PLANT_ID)` — DEKLAROWANY cel misji (elektrownia).
    - `set(col,row)` — FAKTYCZNY sektor lądowania/zrzutu (tama, nie elektrownia).
    - `flyToLocation` MUSI być ostatnie — wymaga wcześniej ustawionej wysokości,
      obiektu docelowego i sektora (dokumentacja API, potwierdzone w komentarzach).
    """
    return [
        "hardReset",
        f"setDestinationObject({PLANT_ID})",
        f"set({col},{row})",
        f"set({_ALTITUDE_M}m)",
        "set(engineON)",
        f"set({_ENGINE_POWER_PERCENT}%)",
        "set(destroy)",
        "set(return)",  # bez tego dron "zostaje utracony na zawsze" (dokumentacja/komentarze)
        "flyToLocation",
    ]


@task("s02e05", hub_name="drone")
class DroneTask(BaseTask):
    """Deterministyczne przeprogramowanie drona — detekcja sektora z mapy, bez LLM/vision."""

    _captured_flag: str | None = None

    def fetch_data(self) -> bytes:
        """Pobiera mapę terenu (statyczna — bezpieczna do cache w LocalCache, w odróżnieniu
        od mutowalnego `electricity.png` z s02e02)."""
        return self.cache.get_or_fetch(
            "drone.png",
            lambda: self.hub.get_data("drone.png", tolerate_503=True),
        )

    def solve(self, data: bytes) -> dict:
        """
        Wykrywa sektor tamy, buduje sekwencję instrukcji i wysyła ją do huba — z jedną
        dodatkową próbą (hardReset + ponowna wysyłka) jeśli pierwsza zostanie odrzucona,
        żeby nie paść ofiarą nawarstwionego złego stanu z poprzednich prób.
        """
        expect_binary(data, "png", source="drone.png")
        dam = detect_dam_sector(data)
        self._save_dam_sector_artifact(dam)
        answer = {"instructions": _build_instructions(col=dam.col, row=dam.row)}

        if self.dry_run:
            # Pętla feedbacku wymaga prawdziwych odpowiedzi huba, żeby wiedzieć czy
            # próbować ponownie — nie ma sensownego trybu "symulowanej" iteracji.
            # --dry-run pokazuje więc TYLKO zbudowaną sekwencję, bez żadnego /verify,
            # zgodnie z kontraktem self.dry_run z innych zadań wieloetapowych
            # (s01e05_railway, s02e04_mailbox) — tu, w odróżnieniu od nich, nie ma co
            # iterować bez sieci, bo cała pętla polega na feedbacku z huba.
            logfire.info("DRY RUN — solve() nie wysyła do huba", sector=(dam.col, dam.row))
            return answer

        last_response: dict | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            response = self.hub.submit(HUB_TASK_NAME, answer)
            last_response = response

            flag = self.hub.get_flag(response)
            if flag:
                self._captured_flag = flag
                return answer

            logfire.warning(
                f"Próba {attempt}/{_MAX_ATTEMPTS} odrzucona przez huba",
                sector=(dam.col, dam.row),
                response=response,
            )

        raise RuntimeError(
            f"Wyczerpano {_MAX_ATTEMPTS} prób dla sektora ({dam.col},{dam.row}) bez flagi. "
            f"Ostatnia odpowiedź huba: {last_response}"
        )

    def _submit(self, task_name: str, answer: Any) -> str | None:
        """Pomija redundantny finalny POST /verify, jeśli solve() już złapało flagę."""
        if self._captured_flag:
            return self._captured_flag
        return super()._submit(task_name, answer)

    @staticmethod
    def _save_dam_sector_artifact(dam: DamSectorResult) -> None:
        """
        Zapisuje wynik deterministycznej detekcji jako `data/output/s02e05_drone/
        dam_sector.json` — ground truth do przyszłej kalibracji vision/promptów, gdyby
        `LLMClient` kiedyś dostał wsparcie dla obrazów (patrz `strategy/s03-readiness.md`,
        sekcja o vision — no-LLM baseline jako złoty wzorzec do porównań).
        """
        _DAM_SECTOR_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        _DAM_SECTOR_ARTIFACT.write_text(
            json.dumps(dam.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logfire.info("Zapisano wynik detekcji sektora tamy", path=str(_DAM_SECTOR_ARTIFACT))
