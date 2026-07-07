#!/usr/bin/env bash
# One-command rebuild of the historical database from scratch (M0 DoD).
#
# Usage: scripts/rebuild.sh
# Requires:
#   - DATABASE_URL (default postgresql://metagame:metagame@localhost:5432/metagame);
#     the role must be allowed to create/drop the target database
#   - data/MTGODecklistCache          (frozen clone; scripts/fetch_data.sh)
#   - data/scryfall/oracle-cards.json (Scryfall bulk data; scripts/fetch_data.sh)
set -euo pipefail
cd "$(dirname "$0")/.."

DATABASE_URL="${DATABASE_URL:-postgresql://metagame:metagame@localhost:5432/metagame}"
export DATABASE_URL
DB_NAME="${DATABASE_URL##*/}"
ADMIN_URL="${DATABASE_URL%/*}/postgres"

echo "== [1/5] recreate database '${DB_NAME}' from scratch"
psql "${ADMIN_URL}" -v ON_ERROR_STOP=1 -q \
    -c "DROP DATABASE IF EXISTS ${DB_NAME} WITH (FORCE)" \
    -c "CREATE DATABASE ${DB_NAME}"

echo "== [2/5] apply migrations"
alembic upgrade head

echo "== [3/5] ingest card data (Scryfall bulk -> cards)"
python -m ingest.scryfall --file data/scryfall/oracle-cards.json

echo "== [4/5] import MTGODecklistCache (import-enabled formats per config/formats.json)"
python -m ingest.cache_import --cache data/MTGODecklistCache

echo "== [5/5] data-quality report"
python -m validation.m0_corpus --out "${REPORT_OUT:-validation/reports/m0-data-quality.md}"

echo "== rebuild complete"
