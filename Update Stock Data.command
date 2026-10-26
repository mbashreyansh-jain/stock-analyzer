#!/bin/zsh
# Double-click this file in Finder to download the latest NSE prices into the database.
# It catches up on every trading day you missed, so it is fine to skip days.

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")" || exit 1

echo "Step 1 of 3: starting the database (Docker)..."
if ! docker info >/dev/null 2>&1; then
  open -a Docker
  for i in {1..60}; do docker info >/dev/null 2>&1 && break; sleep 2; done
fi
docker compose up -d --wait >/dev/null 2>&1 || { echo "Could not start the database. Open the Docker app and try again."; read -k1; exit 1; }

cd services/engine || exit 1
echo "Step 2 of 3: refreshing the NIFTY index member lists..."
uv run stockai universe

echo "Step 3 of 3: downloading prices for any missing trading days..."
LAST=$(docker exec stockai-db psql -U stockai -d stockai -Atc \
  "select coalesce(max(trade_date) + 1, current_date - 7) from ingest_runs where dataset='bhavcopy' and status='ok'")
uv run stockai backfill --start "$LAST"

echo ""
uv run stockai status
echo ""
echo "All done. You can close this window."
read -k1
