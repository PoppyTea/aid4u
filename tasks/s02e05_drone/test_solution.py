"""Testy DroneTask.solve() — mock HubClient + syntetyczna mapa, bez sieci."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from tasks.s02e05_drone import solution

_RED = (220, 20, 20)
_BLUE = (20, 20, 220)
_BG = (200, 200, 180)


def _make_map_with_dam(*, water_col: int = 1, water_row: int = 3) -> bytes:
    """Syntetyczna mapa 3x4 (jak referencyjna) z wodą w jednej komórce (0-indeksowanej)."""
    width, height = 300, 400
    col_lines = [100, 200]
    row_lines = [100, 200, 300]
    arr = np.full((height, width, 3), _BG, dtype=np.uint8)

    for x in col_lines:
        arr[:, x - 2 : x + 3] = _RED
    for y in row_lines:
        arr[y - 2 : y + 3, :] = _RED

    col_bounds = [0, *col_lines, width]
    row_bounds = [0, *row_lines, height]
    x0, x1 = col_bounds[water_col] + 5, col_bounds[water_col + 1] - 5
    y0, y1 = row_bounds[water_row] + 5, row_bounds[water_row + 1] - 5
    arr[y0:y1, x0:x1] = _BLUE

    buf = BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


# Woda w komórce (col=1, row=3) 0-indeksowanej -> sektor 1-indeksowany (2, 4), tak jak
# na referencyjnej mapie (potwierdzone przez map_analysis + niezależnie przez społeczność).
DAM_PNG = _make_map_with_dam(water_col=1, water_row=3)


class _FakeHub:
    """Minimalny podstaw HubClient nagrywający wywołania submit()."""

    def __init__(self, *, submit_responses=None):
        """`submit_responses` to lista kolejnych odpowiedzi — jedna per wywołanie submit()."""
        self.submit_calls: list[tuple[str, dict]] = []
        self._responses = list(submit_responses or [{"flag": "{FLG:LETSFLY}"}])

    def submit(self, task, answer):
        """Nagrywa wywołanie i zwraca kolejną skonfigurowaną odpowiedź (ostatnia się powtarza)."""
        self.submit_calls.append((task, answer))
        idx = min(len(self.submit_calls) - 1, len(self._responses) - 1)
        return self._responses[idx]

    @staticmethod
    def get_flag(response):
        """Odpowiednik HubClient.get_flag — czyta pole 'flag' wprost, bez regexa."""
        return response.get("flag")


def _make_task(hub, *, dry_run=False, tmp_artifact_path=None, monkeypatch=None):
    """Buduje DroneTask z fake hub i (opcjonalnie) przekierowuje artefakt sektora do tmp_path."""
    task = solution.DroneTask(hub=hub, llm=None, dry_run=dry_run)
    if tmp_artifact_path is not None:
        monkeypatch.setattr(solution, "_DAM_SECTOR_ARTIFACT", tmp_artifact_path)
    return task


class TestBuildInstructions:
    """_build_instructions() — kolejność i treść wg kontraktu drone.html."""

    def test_hard_reset_is_first(self):
        """hardReset musi być pierwsze — czyści skumulowany stan z poprzednich prób."""
        instructions = solution._build_instructions(col=2, row=4)
        assert instructions[0] == "hardReset"

    def test_fly_to_location_is_last(self):
        """flyToLocation musi być ostatnie — wymaga wcześniej ustawionej reszty konfiguracji."""
        instructions = solution._build_instructions(col=2, row=4)
        assert instructions[-1] == "flyToLocation"

    def test_contains_destroy_and_return_goals(self):
        """Bez set(return) dron przepada na stałe — oba cele muszą być obecne."""
        instructions = solution._build_instructions(col=2, row=4)
        assert "set(destroy)" in instructions
        assert "set(return)" in instructions

    def test_declares_plant_but_targets_dam_sector(self):
        """Sedno zadania: zadeklarowany cel (elektrownia) i faktyczny sektor (tama) muszą być różne."""
        instructions = solution._build_instructions(col=2, row=4)
        assert f"setDestinationObject({solution.PLANT_ID})" in instructions
        assert "set(2,4)" in instructions
        # Sedno zadania: zadeklarowany cel (elektrownia) != faktyczny sektor (tama).
        assert solution.PLANT_ID not in "set(2,4)"


class TestSolve:
    """DroneTask.solve() — wykrycie sektora + wysyłka + pętla feedbacku."""

    def test_succeeds_on_first_attempt(self, tmp_path, monkeypatch):
        """Poprawnie wykryty sektor + kompletna sekwencja instrukcji dają flagę za pierwszym razem."""
        hub = _FakeHub(submit_responses=[{"flag": "{FLG:LETSFLY}"}])
        task = _make_task(hub, tmp_artifact_path=tmp_path / "dam_sector.json", monkeypatch=monkeypatch)

        answer = task.solve(DAM_PNG)

        assert answer == {"instructions": solution._build_instructions(col=2, row=4)}
        assert len(hub.submit_calls) == 1
        assert task._captured_flag == "{FLG:LETSFLY}"

    def test_retries_once_after_rejection_then_succeeds(self, tmp_path, monkeypatch):
        """Po odrzuceniu solve() ponawia z TYM SAMYM sektorem (hardReset czyści stan), nie zgaduje inny."""
        hub = _FakeHub(
            submit_responses=[
                {"code": -880, "message": "somewhere nearby"},
                {"flag": "{FLG:LETSFLY}"},
            ]
        )
        task = _make_task(hub, tmp_artifact_path=tmp_path / "dam_sector.json", monkeypatch=monkeypatch)

        answer = task.solve(DAM_PNG)

        assert len(hub.submit_calls) == 2
        # Obie próby celują w ten sam (poprawnie wykryty) sektor — nie zgadujemy losowo.
        assert hub.submit_calls[0][1] == hub.submit_calls[1][1] == answer
        assert task._captured_flag == "{FLG:LETSFLY}"

    def test_raises_after_exhausting_max_attempts(self, tmp_path, monkeypatch):
        """Po wyczerpaniu _MAX_ATTEMPTS bez flagi solve() rzuca RuntimeError z diagnostyką, nie cichnie."""
        hub = _FakeHub(submit_responses=[{"code": -880, "message": "nope"}])
        task = _make_task(hub, tmp_artifact_path=tmp_path / "dam_sector.json", monkeypatch=monkeypatch)

        with pytest.raises(RuntimeError, match="Wyczerpano"):
            task.solve(DAM_PNG)

        assert len(hub.submit_calls) == solution._MAX_ATTEMPTS

    def test_dry_run_never_calls_hub_submit(self, tmp_path, monkeypatch):
        """dry_run=True buduje i zwraca sekwencję bez ani jednego POST /verify."""
        artifact_path = tmp_path / "dam_sector.json"
        hub = _FakeHub()
        task = _make_task(hub, dry_run=True, tmp_artifact_path=artifact_path, monkeypatch=monkeypatch)

        answer = task.solve(DAM_PNG)

        assert hub.submit_calls == []
        assert answer == {"instructions": solution._build_instructions(col=2, row=4)}
        assert task._captured_flag is None

    def test_dry_run_does_not_overwrite_dam_sector_artifact(self, tmp_path, monkeypatch):
        """dry_run=True nie nadpisuje commitowanego artefaktu — próbny przebieg nie ma zapisywać wyniku."""
        artifact_path = tmp_path / "dam_sector.json"
        artifact_path.write_text('{"sentinel": "not-overwritten"}', encoding="utf-8")
        hub = _FakeHub()
        task = _make_task(hub, dry_run=True, tmp_artifact_path=artifact_path, monkeypatch=monkeypatch)

        task.solve(DAM_PNG)

        assert artifact_path.read_text(encoding="utf-8") == '{"sentinel": "not-overwritten"}'

    def test_writes_dam_sector_artifact(self, tmp_path, monkeypatch):
        """solve() zapisuje wynik detekcji jako JSON — ground truth do przyszłej kalibracji vision."""
        import json

        artifact_path = tmp_path / "dam_sector.json"
        hub = _FakeHub()
        task = _make_task(hub, tmp_artifact_path=artifact_path, monkeypatch=monkeypatch)

        task.solve(DAM_PNG)

        saved = json.loads(artifact_path.read_text())
        assert saved["col"] == 2
        assert saved["row"] == 4


class TestSubmitDedup:
    """DroneTask._submit() musi pominąć redundantny drugi /verify po sukcesie w solve()."""

    def test_skips_hub_submit_when_flag_already_captured(self):
        """Gdy solve() już złapało flagę, BaseTask.run()'s finalny _submit nie dubluje wywołania."""
        hub = _FakeHub(submit_responses=[{"flag": "{FLG:SHOULD_NOT_BE_CALLED}"}])
        task = solution.DroneTask(hub=hub, llm=None, dry_run=False)
        task._captured_flag = "{FLG:LETSFLY}"

        result = task._submit("drone", {"instructions": []})

        assert result == "{FLG:LETSFLY}"
        assert hub.submit_calls == []

    def test_calls_hub_submit_when_no_flag_was_captured(self):
        """Bez wcześniej złapanej flagi _submit działa jak domyślny BaseTask._submit."""
        hub = _FakeHub(submit_responses=[{"flag": "{FLG:LETSFLY}"}])
        task = solution.DroneTask(hub=hub, llm=None, dry_run=False)

        result = task._submit("drone", {"instructions": []})

        assert result == "{FLG:LETSFLY}"
        assert len(hub.submit_calls) == 1
