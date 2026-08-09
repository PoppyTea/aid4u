#!/usr/bin/env bash
#
# PANIC_BUTTON — awaryjny wyłącznik, Warstwa 0 kill switcha (patrz core/AGENTS.md).
#
# Celowo CZYSTY BASH, zero zależności od Pythona/venv/uv — to ma działać nawet
# gdy środowisko uruchomieniowe jest rozwalone. To jest ostateczna gwarancja
# bezpieczeństwa: jeśli agent/przebieg trzeba zabić, to działa to niezależnie od
# stanu reszty projektu.
#
# Zabija CAŁĄ grupę procesów (znak minus przed PGID w `kill`), nie tylko proces
# główny — inaczej podprocesy (i przyszli subagenci) zostają sierotami.
#
# Użycie: bash scripts/panic.sh   (z dowolnego katalogu)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PGID_FILE="$SCRIPT_DIR/.run/current.pgid"

if [[ ! -f "$PGID_FILE" ]]; then
    echo "Brak $PGID_FILE — nic nie jest aktualnie uruchomione (albo już zabite)." >&2
    exit 1
fi

PGID="$(cat "$PGID_FILE")"

if ! [[ "$PGID" =~ ^[0-9]+$ ]]; then
    echo "Nieprawidłowa zawartość $PGID_FILE: '$PGID'" >&2
    exit 1
fi

# Bezpiecznik: nie zabijaj WŁASNEJ grupy procesów. Normalnie nie powinno się to
# zdarzyć (przebieg odłącza się do własnej grupy przez setsid, więc panic.sh —
# uruchomiony z innej powłoki — jest w innej grupie), ale jeśli plik PGID jest
# nieaktualny/uszkodzony, wysłanie SIGKILL do własnej grupy ubiłoby ten skrypt
# w połowie działania, zanim zdąży posprzątać.
OWN_PGID="$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')"
if [[ -n "$OWN_PGID" && "$PGID" == "$OWN_PGID" ]]; then
    echo "ODMOWA: $PGID_FILE wskazuje na WŁASNĄ grupę procesów tego skryptu ($PGID) — nie zabijam się." >&2
    exit 1
fi

echo "Wysyłam SIGTERM do grupy procesów -$PGID..."
kill -TERM "-$PGID" 2>/dev/null || true

sleep 2

if kill -0 "-$PGID" 2>/dev/null; then
    echo "Grupa wciąż żyje po SIGTERM, wysyłam SIGKILL..."
    kill -KILL "-$PGID" 2>/dev/null || true
fi

rm -f "$PGID_FILE"
echo "Gotowe."
