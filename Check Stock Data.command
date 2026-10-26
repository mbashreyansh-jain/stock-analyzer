#!/bin/zsh
# Double-click this file in Finder to see what data is loaded and whether anything looks wrong.

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")" || exit 1

if ! docker info >/dev/null 2>&1; then
  echo "Starting Docker..."
  open -a Docker
  for i in {1..60}; do docker info >/dev/null 2>&1 && break; sleep 2; done
fi
docker compose up -d --wait >/dev/null 2>&1

cd services/engine || exit 1
uv run stockai status
echo ""
echo "Latest prices for RELIANCE as an example:"
uv run stockai show RELIANCE --days 5
echo ""
echo "You can close this window."
read -k1
