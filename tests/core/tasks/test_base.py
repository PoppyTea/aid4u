import json
import re

import pytest

from core.tasks.base import BaseTask


class _DummyTask(BaseTask):
    def solve(self, data):
        return data


@pytest.fixture
def dummy_task(tmp_path, monkeypatch):
    """BaseTask z podmienionym .cache/ i data/outputs/ na tmp_path — bez śmiecenia w repo."""
    monkeypatch.setattr("core.hub.cache._CACHE_ROOT", tmp_path / ".cache")
    outputs_dir = tmp_path / "outputs"
    monkeypatch.setattr("core.tasks.base._OUTPUTS_DIR", outputs_dir)

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
        assert json.loads(path.read_text(encoding="utf-8")) == [{"name": "Jan", "tags": ["transport"]}]

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
