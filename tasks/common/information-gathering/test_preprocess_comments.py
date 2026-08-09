"""Testy preprocess_comments.py — walidacja ścieżek + Base64/thread-grouping."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# Import przez ścieżkę pliku (nie zwykły `import`) — katalog nadrzędny ma myślnik
# w nazwie ("information-gathering"), więc nie jest poprawnym identyfikatorem pakietu.
SCRIPT_PATH = Path(__file__).resolve().parent / "preprocess_comments.py"
_spec = importlib.util.spec_from_file_location("preprocess_comments", str(SCRIPT_PATH))
preprocess_comments = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preprocess_comments)
process_comments = preprocess_comments.process_comments


@pytest.fixture
def workspace_temp_file():
    """Plik tymczasowy WEWNĄTRZ workspace roota — poza nim `process_comments()` odmówi."""
    workspace_root = preprocess_comments._find_workspace_root(SCRIPT_PATH.parent)
    test_dir = workspace_root / "tasks" / "common" / "information-gathering" / "temp_test_data"
    test_dir.mkdir(parents=True, exist_ok=True)

    temp_file = test_dir / "test_comments.md"
    yield temp_file

    if temp_file.exists():
        temp_file.unlink()
    preprocessed = test_dir / "test_comments_preprocessed.md"
    if preprocessed.exists():
        preprocessed.unlink()
    if test_dir.exists():
        try:
            test_dir.rmdir()
        except OSError:
            pass


def test_process_comments_success(workspace_temp_file):
    """Base64 rozkodowany + wątki poprawnie owinięte w <THREAD> dla pliku wewnątrz workspace."""
    content = (
        "--- Komentarz od: John Doe\n"
        "Hello, this is a normal comment with some Base64: "
        "SGVsbG8gV29ybGQgZnJvbSBKYXBhbiB0byBBbWVyaWNhIQ==\n"
        "--- Komentarz od: Jane Doe\n"
        "Another comment thread here.\n"
    )
    workspace_temp_file.write_text(content, encoding="utf-8")

    output = process_comments(workspace_temp_file)

    assert "[DECODED_BASE64]: Hello World from Japan to America!" in output
    assert "<THREAD>" in output
    assert "</THREAD>" in output


def test_process_comments_path_traversal_rejection(tmp_path):
    """Plik spoza workspace roota (np. /tmp) musi zostać odrzucony."""
    outside_file = tmp_path / "unsafe.md"
    outside_file.write_text("Some text", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        process_comments(outside_file)

    assert "is outside workspace root" in str(exc_info.value)


def test_cli_path_traversal_rejection(tmp_path):
    """CLI (subprocess) odmawia przetworzenia pliku spoza workspace roota."""
    outside_file = tmp_path / "unsafe.md"
    outside_file.write_text("Some text", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(outside_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Access denied" in result.stderr or "Access denied" in result.stdout


def test_cli_success(workspace_temp_file):
    """CLI end-to-end: plik wewnątrz workspace roota przetwarza się i zapisuje wynik."""
    content = "--- Komentarz od: John Doe\nHello there\n"
    workspace_temp_file.write_text(content, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(workspace_temp_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    preprocessed_path = workspace_temp_file.with_name("test_comments_preprocessed.md")
    assert preprocessed_path.exists()
    assert "<THREAD>" in preprocessed_path.read_text(encoding="utf-8")


def test_cli_refuses_when_output_would_overwrite_input(tmp_path, monkeypatch):
    """Plik bez '.md' w nazwie: output_path nie może cicho pokryć się z input_path."""
    workspace_root = preprocess_comments._find_workspace_root(SCRIPT_PATH.parent)
    no_ext_dir = workspace_root / "tasks" / "common" / "information-gathering" / "temp_test_data2"
    no_ext_dir.mkdir(parents=True, exist_ok=True)
    no_ext_file = no_ext_dir / "notes"
    no_ext_file.write_text("--- Komentarz od: X\nhello\n", encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(no_ext_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "same as input" in result.stderr or "same as input" in result.stdout
        # Plik źródłowy MUSI przetrwać nietknięty — to jest cała treść tego testu.
        assert no_ext_file.read_text(encoding="utf-8") == "--- Komentarz od: X\nhello\n"
    finally:
        no_ext_file.unlink(missing_ok=True)
        no_ext_dir.rmdir()
