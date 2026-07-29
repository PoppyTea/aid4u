#!/usr/bin/env python3
"""
Import sekrety z sekcji keyring w .env do systemowego keyring.

Użycie:
    uv run scripts/import_keyring.py           # Import wszystkich kluczy
    uv run import-keyring.py --limited         # Import tylko kluczy z listy
    uv run scripts/import_keyring.py --force   # Nadpisz istniejące
    uv run scripts/import_keyring.py --check   # Tylko sprawdzenie
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import keyring


KEYRING_SERVICE = "aid4u"
LIMITED_KEYS = False
KEYRING_KEYS = {
    "APIKEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_PREMIUM",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LOGFIRE_TOKEN",
    "VPS_HOST",
}

KEYRING_SECTION_START = "# =========|> keyring aid4u |>"
KEYRING_SECTION_END = "# =========<| keyring aid4u <|"


def find_keyring_section(env_path: Path) -> dict[str, str]:
    """Wyciągnij sekrety z sekcji keyring w .env."""
    content = env_path.read_text()

    # Znajdź sekcję między markerami
    pattern = rf"{re.escape(KEYRING_SECTION_START)}(.*?){re.escape(KEYRING_SECTION_END)}"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {}

    section = match.group(1)
    secrets = {}

    # Parsuj key=value
    for line in section.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")

            if LIMITED_KEYS and key not in KEYRING_KEYS:
                continue
            secrets[key] = value

    return secrets


def import_to_keyring(secrets: dict[str, str], force: bool = False) -> None:
    """Importuj sekrety do keyring."""
    imported = 0
    skipped = 0

    for key, value in secrets.items():
        if not value:
            print(f"⊘ Pusta wartość: {key}")
            skipped += 1
            continue

        # Sprawdź czy już istnieje tylko jeśli nie wymuszamy nadpisania
        if not force:
            existing = keyring.get_password(KEYRING_SERVICE, key)
            if existing:
                print(f"⊘ Już istnieje (--force żeby nadpisać): {key}")
                skipped += 1
                continue

        try:
            keyring.set_password(KEYRING_SERVICE, key, value)
            print(f"✓ Imported: {key}")
            imported += 1
        except Exception as e:
            print(f"✗ Error importing {key}: {e}")
            skipped += 1

    print(f"\n✓ Imported: {imported} | ⊘ Skipped: {skipped}")


def check_keyring(secrets: dict[str, str]) -> None:
    """Sprawdź czy sekrety w keyring są identyczne z .env."""
    print("\n🔍 Checking keyring vs .env:\n")

    matches = 0
    mismatches = 0

    for key, env_value in secrets.items():
        keyring_value = keyring.get_password(KEYRING_SERVICE, key)

        if keyring_value == env_value:
            print(f"✓ Match: {key}")
            matches += 1
        elif keyring_value is None:
            print(f"⊘ Not in keyring: {key}")
            mismatches += 1
        else:
            print(f"✗ MISMATCH: {key}")
            print(f"    .env:    {env_value[:20]}...")
            print(f"    keyring: {keyring_value[:20]}...")
            mismatches += 1

    print(f"\n✓ Matches: {matches} | ✗ Mismatches: {mismatches}")


def main() -> None:
    global LIMITED_KEYS
    parser = argparse.ArgumentParser(description="Import sekrety z .env do systemowego keyring")
    parser.add_argument("--force", action="store_true", help="Nadpisz istniejące klucze")
    parser.add_argument("--check", action="store_true", help="Tylko sprawdź (nie importuj)")
    parser.add_argument("--limited", action="store_true", help="Importuj tylko klucze z listy")
    LIMITED_KEYS = parser.parse_known_args()[0].limited

    args = parser.parse_args()

    # Znajdź .env
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print(f"✗ .env nie znaleziony: {env_path}")
        sys.exit(1)

    print(f"📄 Reading: {env_path}\n")

    # Wyciągnij sekcję keyring
    secrets = find_keyring_section(env_path)

    if not secrets:
        print("✗ Sekcja keyring nie znaleziona w .env")
        print(f"   Powinno być między: {KEYRING_SECTION_START}")
        print(f"   A: {KEYRING_SECTION_END}")
        sys.exit(1)

    print(f"Found {len(secrets)} keys in .env keyring section:\n")
    for key in secrets:
        print(f"  • {key}")

    if args.check:
        check_keyring(secrets)
    else:
        print()
        import_to_keyring(secrets, force=args.force)
        print("\n✓ Done! Możesz teraz usunąć sekrety z .env jeśli są w keyring.")


if __name__ == "__main__":
    main()
