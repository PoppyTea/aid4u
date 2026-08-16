import json
import os
import re
from contextlib import contextmanager

import pytest

from core.runtime import killswitch
from core.tasks.base import BaseTask


class _DummyTask(BaseTask):
    def solve(self, data):
        return data


@pytest.fixture
def dummy_task(tmp_path, monkeypatch):
    """BaseTask z podmienionym .cache/, data/run-history/ i .run/ na tmp_path — bez śmiecenia w repo.

    Izoluje też killswitch (patrz tests/core/runtime/test_killswitch.py::_isolated_run_dir) —
    run() woła teraz start_run()/end_run() naprawdę, więc bez tego testy dotykałyby
    prawdziwego .run/ repozytorium i odłączałyby proces pytest od sesji terminala
    przez realny os.setsid().
    """
    monkeypatch.setattr("core.hub.cache._CACHE_ROOT", tmp_path / ".cache")
    outputs_dir = tmp_path / "outputs"
    monkeypatch.setattr("core.tasks.base._OUTPUTS_DIR", outputs_dir)

    run_dir = tmp_path / ".run"
    monkeypatch.setattr(killswitch, "_RUN_DIR", run_dir)
    monkeypatch.setattr(killswitch, "_PGID_FILE", run_dir / "current.pgid")
    monkeypatch.setattr(killswitch, "_STOP_FILE", run_dir / "STOP")
    monkeypatch.setattr(os, "setsid", lambda: None)
    killswitch.end_run()

    task = _DummyTask(hub=None, llm=None)
    task._task_name = "s99e99"
    return task, outputs_dir


def _written_file(outputs_dir):
    files = list(outputs_dir.iterdir())
    assert len(files) == 1, f"Oczekiwano dokładnie jednego pliku, jest: {files}"
    return files[0]


class TestSaveOutput:
    def test_filename_pattern_falls_back_to_answer_json_without_source_file(self, dummy_task):
        task, outputs_dir = dummy_task
        task._save_output({"tags": ["transport"]})

        path = _written_file(outputs_dir)
        assert re.fullmatch(r"s99e99-\d{4}-\d{6}-answer\.json", path.name), path.name

    def test_filename_uses_source_file_name_from_cache_last_key(self, dummy_task):
        task, outputs_dir = dummy_task
        task.cache.last_key = "people.csv"
        task._save_output([{"name": "Jan"}])

        path = _written_file(outputs_dir)
        assert re.fullmatch(r"s99e99-\d{4}-\d{6}-people\.csv", path.name), path.name

    def test_dict_and_list_answers_written_as_json(self, dummy_task):
        task, outputs_dir = dummy_task
        task._save_output([{"name": "Jan", "tags": ["transport"]}])

        path = _written_file(outputs_dir)
        assert json.loads(path.read_text(encoding="utf-8")) == [
            {"name": "Jan", "tags": ["transport"]}
        ]

    def test_string_answer_written_as_plain_text(self, dummy_task):
        task, outputs_dir = dummy_task
        task._save_output("FLG:abc123")

        path = _written_file(outputs_dir)
        assert path.read_text(encoding="utf-8") == "FLG:abc123"

    def test_bytes_answer_written_as_raw_bytes(self, dummy_task):
        task, outputs_dir = dummy_task
        task._save_output(b"\x00\x01raw-bytes")

        path = _written_file(outputs_dir)
        assert path.read_bytes() == b"\x00\x01raw-bytes"

    def test_creates_outputs_directory_if_missing(self, dummy_task):
        task, outputs_dir = dummy_task
        assert not outputs_dir.exists()

        task._save_output({"x": 1})

        assert outputs_dir.exists()

    def test_run_saves_output_before_submit(self, dummy_task, monkeypatch):
        task, outputs_dir = dummy_task
        monkeypatch.setattr(task, "fetch_data", lambda: None)
        monkeypatch.setattr(task, "solve", lambda data: {"result": "ok"})
        monkeypatch.setattr(task, "_submit", lambda task_name, answer: None)

        task.run()

        path = _written_file(outputs_dir)
        assert json.loads(path.read_text(encoding="utf-8")) == {"result": "ok"}


class TestKillSwitchIntegration:
    """
    Weryfikuje że kill switch jest faktycznie WPIĘTY w BaseTask.run(), nie tylko że
    jego prymitywy (check_abort/start_run/end_run) działają w izolacji — to drugie
    już pokrywa tests/core/runtime/test_killswitch.py, ale nic tam nie sprawdzało
    punktu połączenia z run().
    """

    def test_check_abort_runs_before_fetch_data(self, dummy_task, monkeypatch):
        """Budżet wall-clock=0 musi zablokować fetch_data() — check_abort() woła się PRZED nim, nie tylko przed submit.

        Celowo używa budżetu czasu, nie .run/STOP: start_run() poprawnie czyści
        STOP na starcie każdego przebiegu (patrz jego docstring), więc STOP
        ustawione przed task.run() nigdy by nie przetrwało do check_abort() —
        budżet=0 to jedyny sposób na deterministyczne wymuszenie AbortRun
        dokładnie w tym miejscu.
        """
        task, _ = dummy_task
        task._max_seconds = 0
        fetch_data_called = False

        def spy_fetch_data():
            nonlocal fetch_data_called
            fetch_data_called = True
            return None

        monkeypatch.setattr(task, "fetch_data", spy_fetch_data)

        result = task.run()

        assert result is None
        assert not fetch_data_called, "fetch_data() nie powinno wystartować — check_abort() miał to złapać wcześniej"

    def test_abort_run_from_solve_returns_none_cleanly(self, dummy_task, monkeypatch):
        """AbortRun rzucone z solve() (np. przez check_abort() w pętli agenta) daje czyste run() -> None, nie wyjątek."""
        task, _ = dummy_task

        def aborting_solve(data):
            raise killswitch.AbortRun("Przerwano przez .run/STOP (graceful stop).")

        monkeypatch.setattr(task, "fetch_data", lambda: None)
        monkeypatch.setattr(task, "solve", aborting_solve)

        result = task.run()  # nie powinno rzucić

        assert result is None

    def test_start_run_and_end_run_are_called(self, dummy_task, monkeypatch):
        """run() musi wołać start_run() na starcie i end_run() na końcu (sukces) — cykl życia .run/ zależy od obu.

        Patchuje `core.tasks.base.start_run`/`end_run`, NIE `killswitch.start_run`
        — `base.py` importuje te nazwy przez `from core.runtime import ...`, więc
        patchowanie źródłowego modułu nie wpłynęłoby na już-zaimportowaną lokalną
        referencję w `base.py` (klasyczna pułapka "patch where it's used").
        """
        task, _ = dummy_task
        calls = []
        monkeypatch.setattr("core.tasks.base.start_run", lambda **kw: calls.append(("start_run", kw)))
        monkeypatch.setattr("core.tasks.base.end_run", lambda: calls.append(("end_run",)))
        monkeypatch.setattr(task, "fetch_data", lambda: None)
        monkeypatch.setattr(task, "solve", lambda data: {"result": "ok"})
        monkeypatch.setattr(task, "_submit", lambda task_name, answer: None)

        task.run()

        names = [c[0] for c in calls]
        assert names == ["start_run", "end_run"], f"oczekiwano start_run przed end_run, dostano: {names}"

    def test_end_run_called_even_when_solve_raises(self, dummy_task, monkeypatch):
        """end_run() (sprzątanie .run/) musi się wykonać nawet gdy solve() rzuca zwykły wyjątek, nie tylko na happy path."""
        task, _ = dummy_task
        end_run_called = False

        def spy_end_run():
            nonlocal end_run_called
            end_run_called = True

        monkeypatch.setattr("core.tasks.base.end_run", spy_end_run)
        monkeypatch.setattr(task, "fetch_data", lambda: None)
        monkeypatch.setattr(task, "solve", lambda data: (_ for _ in ()).throw(RuntimeError("boom")))

        with pytest.raises(RuntimeError, match="boom"):
            task.run()

        assert end_run_called


class TestObservabilitySessionContext:
    """
    `propagate_attrs()` istniał w `core/observability/decorators.py` od dawna, ale
    nigdy nie był wywoływany — bez tego każda generacja Langfuse lądowała w panelu
    bez żadnego kontekstu sesji (patrz strategy/observability.md, 2026-08-16).
    """

    def test_propagate_attrs_called_with_task_name_and_session_id(self, dummy_task, monkeypatch):
        task, _ = dummy_task
        captured = {}

        @contextmanager
        def fake_propagate_attrs(**kwargs):
            captured.update(kwargs)
            yield

        monkeypatch.setattr("core.tasks.base.propagate_attrs", fake_propagate_attrs)
        monkeypatch.setattr(task, "fetch_data", lambda: None)
        monkeypatch.setattr(task, "solve", lambda data: {"result": "ok"})
        monkeypatch.setattr(task, "_submit", lambda task_name, answer: None)

        task.run()

        assert captured["trace_name"] == "s99e99"
        # Sufiks losowy (8 hex) na końcu — bez niego dwa uruchomienia w tej samej
        # sekundzie kolidowałyby (patrz base.py, komentarz przy session_id).
        assert re.fullmatch(r"s99e99-\d{4}-\d{6}-[0-9a-f]{8}", captured["session_id"]), captured[
            "session_id"
        ]

    def test_propagate_attrs_session_id_is_unique_across_runs_in_the_same_second(
        self, dummy_task, monkeypatch
    ):
        """Regresja: session_id bez losowego sufiksu miał rozdzielczość 1 sekundy — dwa
        uruchomienia tego samego zadania w tej samej sekundzie dostawały identyczny
        session_id i ich generacje zlewały się w Langfuse w jedną sesję."""
        task, _ = dummy_task
        captured_ids = []

        @contextmanager
        def fake_propagate_attrs(**kwargs):
            captured_ids.append(kwargs["session_id"])
            yield

        monkeypatch.setattr("core.tasks.base.propagate_attrs", fake_propagate_attrs)
        monkeypatch.setattr(task, "fetch_data", lambda: None)
        monkeypatch.setattr(task, "solve", lambda data: {"result": "ok"})
        monkeypatch.setattr(task, "_submit", lambda task_name, answer: None)

        task.run()
        task.run()

        assert captured_ids[0] != captured_ids[1]
