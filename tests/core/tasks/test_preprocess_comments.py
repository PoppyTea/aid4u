import importlib.util
import subprocess
import sys
from pathlib import Path
import pytest

# Load the preprocess_comments module dynamically from its absolute file path because its directory contains a hyphen
script_path = (
    Path(__file__).resolve().parents[3]
    / "tasks"
    / "common"
    / "information-gathering"
    / "preprocess_comments.py"
)
spec = importlib.util.spec_from_file_location("preprocess_comments", str(script_path))
preprocess_comments = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preprocess_comments)
process_comments = preprocess_comments.process_comments


@pytest.fixture
def workspace_temp_file():
    # Create a temporary file inside /app (the workspace)
    workspace_root = Path(__file__).resolve().parents[3]
    test_dir = workspace_root / "tests" / "core" / "tasks" / "temp_test_data"
    test_dir.mkdir(parents=True, exist_ok=True)

    temp_file = test_dir / "test_comments.md"
    yield temp_file

    # Cleanup
    if temp_file.exists():
        temp_file.unlink()
    # Cleanup preprocessed file if created
    preprocessed = test_dir / "test_comments_preprocessed.md"
    if preprocessed.exists():
        preprocessed.unlink()
    if test_dir.exists():
        try:
            test_dir.rmdir()
        except OSError:
            pass


def test_process_comments_success(workspace_temp_file):
    # Write normal data
    content = (
        "--- Komentarz od: John Doe\n"
        "Hello, this is a normal comment with some Base64: "
        "SGVsbG8gV29ybGQgZnJvbSBKYXBhbiB0byBBbWVyaWNhIQ==\n"
        "--- Komentarz od: Jane Doe\n"
        "Another comment thread here.\n"
    )
    workspace_temp_file.write_text(content, encoding="utf-8")

    # Process
    output = process_comments(workspace_temp_file)

    # Check that it decoded the base64 and wrapped in <THREAD>
    assert "[DECODED_BASE64]: Hello World from Japan to America!" in output
    assert "<THREAD>" in output
    assert "</THREAD>" in output


def test_process_comments_path_traversal_rejection(tmp_path):
    # Create a file outside of the workspace (e.g. in /tmp via tmp_path)
    outside_file = tmp_path / "unsafe.md"
    outside_file.write_text("Some text", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        process_comments(outside_file)

    assert "is outside workspace root" in str(exc_info.value)


def test_cli_path_traversal_rejection(tmp_path):
    # Run the script as a subprocess and pass an outside path
    outside_file = tmp_path / "unsafe.md"
    outside_file.write_text("Some text", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(script_path), str(outside_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Access denied" in result.stderr or "Access denied" in result.stdout


def test_cli_success(workspace_temp_file):
    # Write normal data
    content = "--- Komentarz od: John Doe\nHello there\n"
    workspace_temp_file.write_text(content, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(script_path), str(workspace_temp_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    preprocessed_path = workspace_temp_file.with_name("test_comments_preprocessed.md")
    assert preprocessed_path.exists()
    assert "<THREAD>" in preprocessed_path.read_text(encoding="utf-8")
