"""Pobiera pliki Systemu Przesyłek Konduktorskich z hub.ag3nts.org.

Czyta SPK_files_list.csv (jedna nazwa pliku na linię), pobiera brakujące pliki
do system-przesylek-konduktorskich/, a potem doszukuje się w pobranej treści
kolejnych referencji `include file="..."`, dopisując nowe nazwy do listy —
aż kolejka się wyczerpie (BFS po grafie include'ów).

Użycie:
    uv run python data/input/s01e04_sendit/fetch_spk_files.py
"""

from __future__ import annotations

from core.observability.setup import setup_observability

setup_observability()

import re
from pathlib import Path

from core.hub.client import HubClient

DOCS_DIR = Path(__file__).parent / "system-przesylek-konduktorskich"
FILE_LIST = DOCS_DIR / "SPK_files_list.csv"
INCLUDE_PATTERN = re.compile(r'(?<=include file\=")(?P<file_name>.*?\..{1,4})(?=")', flags=re.MULTILINE)


def _safe_rel_path(raw: Path) -> Path:
    """Odrzuca ścieżki bezwzględne i próby wyjścia poza DOCS_DIR (np. `../../etc/passwd`)."""
    if raw.is_absolute():
        raise ValueError(f"Ścieżka bezwzględna niedozwolona w manifeście/include: {raw}")
    root = DOCS_DIR.resolve()
    candidate = (DOCS_DIR / raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Ścieżka poza dozwolonym katalogiem: {raw}")
    return candidate.relative_to(root)


def _read_file_list() -> set[Path]:
    if not FILE_LIST.exists():
        return set()
    lines = FILE_LIST.read_text(encoding="utf-8").splitlines()
    return {_safe_rel_path(Path(line.strip())) for line in lines if line.strip()}


def _append_to_file_list(new_paths: list[Path]) -> None:
    with FILE_LIST.open("a", encoding="utf-8") as f:
        for path in new_paths:
            f.write(f"{path}\n")


def fetch_all() -> list[Path]:
    """Pobiera brakujące pliki i zwraca listę nowo pobranych ścieżek."""
    hub = HubClient()
    known: set[Path] = _read_file_list()
    queue: list[Path] = list(known)
    new_entries: list[Path] = []
    downloaded: list[Path] = []

    i = 0
    while i < len(queue):
        rel_path = queue[i]
        i += 1
        dest = DOCS_DIR / rel_path

        if dest.exists():
            content = dest.read_bytes()
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            content = hub.get_public(f"dane/doc/{rel_path.as_posix()}")
            dest.write_bytes(content)
            downloaded.append(rel_path)

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue  # plik binarny (np. .png) — nic do zregexowania

        for match in INCLUDE_PATTERN.finditer(text):
            ref = _safe_rel_path(Path(match.group("file_name")))
            if ref not in known:
                known.add(ref)
                queue.append(ref)
                new_entries.append(ref)

    if new_entries:
        _append_to_file_list(new_entries)

    return downloaded


if __name__ == "__main__":
    result = fetch_all()
    print(f"Pobrano {len(result)} nowych plików:")
    for path in result:
        print(f"  {path}")
