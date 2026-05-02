#!/usr/bin/env bash
# Deployment na VPS — jedno polecenie: ./deploy/deploy.sh
#
# Wymagania:
#   - SSH key skonfigurowany dla $VPS_USER@$VPS_HOST
#   - uv zainstalowany na VPS
#   - plik .env na VPS w /opt/aid4u/.env
#
# Pierwsze uruchomienie na VPS:
#   ssh user@vps "mkdir -p /opt/aid4u && git clone <repo-url> /opt/aid4u"
#   scp .env user@vps:/opt/aid4u/.env

set -euo pipefail

source .env 2>/dev/null || true

VPS_HOST="${VPS_HOST:?Ustaw VPS_HOST w .env}"
VPS_USER="${VPS_USER:?Ustaw VPS_USER w .env}"
VPS_PATH="${VPS_PATH:-/opt/aid4u}"
SERVICE="${1:-}"  # opcjonalna nazwa serwisu do restartu, np. aid4u-proxy

echo "▶ Deploying to $VPS_USER@$VPS_HOST:$VPS_PATH"

ssh "$VPS_USER@$VPS_HOST" bash <<REMOTE
  set -euo pipefail
  cd "$VPS_PATH"

  echo "  → git pull"
  git pull --ff-only

  echo "  → uv sync"
  uv sync --frozen

  if [ -n "$SERVICE" ]; then
    echo "  → restarting $SERVICE"
    sudo systemctl restart "$SERVICE"
    sudo systemctl status "$SERVICE" --no-pager -l
  fi

  echo "  ✓ Done"
REMOTE
