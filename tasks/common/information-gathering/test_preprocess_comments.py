import os
import sys
import pytest

# Add the local directory to sys.path to allow importing from a directory with a hyphen
sys.path.insert(0, os.path.dirname(__file__))
from preprocess_comments import process_comments


def test_process_comments_valid_path(tmp_path):
    # Create a dummy file in a valid directory
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    test_file = allowed_dir / "comments.md"
    content = "--- Komentarz od: John\nSGVsbG8gV29ybGQhIEhlbGxvIFdvcmxkISBIZWxsbyBXb3JsZCEgSGVsbG8gV29ybGQh\n"  # base64 for longer text
    test_file.write_text(content, encoding="utf-8")

    # Process with the allowed_dir parameter set to allowed_dir
    res = process_comments(str(test_file), allowed_dir=str(allowed_dir))

    assert "<THREAD>" in res
    assert "[DECODED_BASE64]: Hello World! Hello World! Hello World! Hello World!" in res


def test_process_comments_path_traversal(tmp_path):
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    # File outside the allowed directory
    forbidden_dir = tmp_path / "forbidden"
    forbidden_dir.mkdir()

    test_file = forbidden_dir / "secret.md"
    test_file.write_text("secret", encoding="utf-8")

    # This should raise a ValueError
    with pytest.raises(ValueError) as exc_info:
        process_comments(str(test_file), allowed_dir=str(allowed_dir))

    assert "Path traversal detected" in str(exc_info.value)


def test_process_comments_traversal_using_parent_dots(tmp_path):
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    # Attempting path traversal with ".."
    traversal_path = allowed_dir / "../forbidden/secret.md"

    with pytest.raises(ValueError) as exc_info:
        process_comments(str(traversal_path), allowed_dir=str(allowed_dir))

    assert "Path traversal detected" in str(exc_info.value)
