#!/usr/bin/env bash
# Wystawia lokalny port publicznie przez ngrok — dla zadań, do których
# zewnętrzny bot (np. Wojtek w s01e03) musi się dobić przez internet.
#
# Wymagania (jednorazowo, na maszynie uruchamiającej tunel):
#   1. Zainstaluj ngrok: https://ngrok.com/download
#   2. Uwierzytelnij:   ngrok config add-authtoken <twój-token>
#
# Użycie:
#   ./deploy/ngrok_tunnel.sh [port]     # domyślnie 8003 (s01e03 proxy)
#
# Publiczny URL pojawi się w output ngrok (https://*.ngrok-free.app) —
# to jest adres do podania botowi grading na hubie.

set -euo pipefail

PORT="${1:-8003}"

if ! command -v ngrok &> /dev/null; then
    echo "✗ ngrok nie jest zainstalowany. Zobacz komentarz na górze tego skryptu." >&2
    exit 1
fi

echo "▶ Wystawiam port $PORT publicznie przez ngrok — Ctrl+C żeby zamknąć tunel."
exec ngrok http "$PORT"
