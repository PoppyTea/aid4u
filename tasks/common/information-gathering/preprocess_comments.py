import base64
from pathlib import Path
import re
import sys


def _find_workspace_root(start: Path) -> Path:
    """
    Szuka roota repo idąc w górę od `start` aż do katalogu z `pyproject.toml`.

    Zamiast zahardkodowanej głębokości (`parents[N]`), która cicho wskazywałaby
    złe miejsce, gdyby ten plik kiedyś się przeniósł — ten sposób zostaje
    poprawny niezależnie od tego, jak głęboko w drzewie repo mieszka.
    """
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"Nie znaleziono roota repo (pyproject.toml) powyżej {start}")


def process_comments(filepath):
    """
    Reads and preprocesses a comments file by decoding Base64 segments and grouping threads.
    """
    # Convert to Path and resolve absolute path to prevent path traversal
    path = Path(filepath).resolve()
    workspace_root = _find_workspace_root(Path(__file__).resolve().parent)
    if not path.is_relative_to(workspace_root):
        raise ValueError(f"Access denied: Path '{path}' is outside workspace root.")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Base64 decoding
    # Szukamy ciągów znaków (A-Za-z0-9+/=) o długości min 40, bez białych znaków,
    # które można poprawnie zdekodować jako UTF-8 i mają sens.
    b64_pattern = re.compile(r"\b[A-Za-z0-9+/=]{40,}\b")

    def b64_replace(match):
        encoded = match.group(0)
        try:
            # Pad if necessary
            missing_padding = len(encoded) % 4
            if missing_padding:
                encoded += "=" * (4 - missing_padding)
            decoded_bytes = base64.b64decode(encoded, validate=True)
            decoded_str = decoded_bytes.decode("utf-8")
            # Only replace if decoded string seems like text (e.g. contains spaces, printable chars)
            if re.search(r"[a-zA-Z0-9]", decoded_str) and len(decoded_str) > 5:
                return f"{match.group(0)}\n[DECODED_BASE64]: {decoded_str}\n"
        except Exception:
            pass
        return match.group(0)

    content = b64_pattern.sub(b64_replace, content)

    # 2. Thread grouping
    threads = []
    current_thread = []

    for line in content.splitlines():
        if line.startswith("--- Komentarz od:"):
            if current_thread:
                threads.append("\n".join(current_thread))
            current_thread = [line]
        else:
            current_thread.append(line)
    if current_thread:
        threads.append("\n".join(current_thread))

    # Wrap each thread in <THREAD> tags
    final_content = []
    for t in threads:
        if t.strip():
            final_content.append(f"<THREAD>\n{t}\n</THREAD>\n")

    return "\n".join(final_content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python preprocess_comments.py <file.md>")
        sys.exit(1)

    input_file = sys.argv[1]
    workspace_root = _find_workspace_root(Path(__file__).resolve().parent)

    try:
        # Sanitize and validate input path
        input_path = Path(input_file).resolve()
        if not input_path.is_relative_to(workspace_root):
            raise ValueError(
                f"Access denied: Input file '{input_path}' must be inside workspace root '{workspace_root}'."
            )

        if not input_path.is_file():
            raise FileNotFoundError(f"Input file not found: '{input_path}'")

        output_content = process_comments(input_path)

        # Sanitize and validate output path
        output_file_str = str(input_path).replace(".md", "_preprocessed.md")
        output_path = Path(output_file_str).resolve()

        if not output_path.is_relative_to(workspace_root):
            raise ValueError(
                f"Access denied: Output file '{output_path}' must be inside workspace root '{workspace_root}'."
            )
        if output_path == input_path:
            # input_file bez ".md" w nazwie: .replace() nie ma czego zamienić,
            # więc output_path wyszedłby identyczny z input_path — bez tej
            # asercji zapis niżej cicho nadpisałby źródłowy plik jego własnym
            # zdekodowanym/pogrupowanym w wątki przetworzeniem.
            raise ValueError(
                f"Refusing to write: output path '{output_path}' is the same as input "
                f"(input file has no '.md' extension to replace)."
            )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_content)

        print(f"Preprocessed {input_path} into {output_path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
