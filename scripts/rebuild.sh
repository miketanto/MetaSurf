#!/usr/bin/env bash
# One-command rebuild of the historical database from scratch (M0 DoD).
#
# Usage: scripts/rebuild.sh
# Requires:
#   - DATABASE_URL (default postgresql://metagame:metagame@localhost:5432/metagame);
#     the role must be allowed to create/drop the target database
#   - data/MTGODecklistCache           (frozen clone; scripts/fetch_data.sh)
#   - data/scryfall/oracle-cards.jsonl (Scryfall bulk data; scripts/fetch_data.sh;
#     the legacy .json array framing is accepted as a fallback)
set -euo pipefail
cd "$(dirname "$0")/.."

DATABASE_URL="${DATABASE_URL:-postgresql://metagame:metagame@localhost:5432/metagame}"
export DATABASE_URL
DB_NAME="${DATABASE_URL##*/}"
ADMIN_URL="${DATABASE_URL%/*}/postgres"

echo "== [1/7] recreate database '${DB_NAME}' from scratch"
psql "${ADMIN_URL}" -v ON_ERROR_STOP=1 -q \
    -c "DROP DATABASE IF EXISTS ${DB_NAME} WITH (FORCE)" \
    -c "CREATE DATABASE ${DB_NAME}"

echo "== [2/7] apply migrations"
alembic upgrade head

echo "== [3/7] ingest card data (Scryfall bulk -> cards)"
if [ -f data/scryfall/oracle-cards.jsonl ]; then
    python -m ingest.scryfall --file data/scryfall/oracle-cards.jsonl
else
    python -m ingest.scryfall --file data/scryfall/oracle-cards.json
fi

echo "== [4/7] import MTGODecklistCache (import-enabled formats per config/formats.json)"
python -m ingest.cache_import --cache data/MTGODecklistCache

echo "== [5/7] data-quality report"
python -m validation.m0_corpus --out "${REPORT_OUT:-validation/reports/m0-data-quality.md}"

echo "== [6/7] batch archetype labeling (M2)"
python -m archetypes.labeler

echo "== [7/7] match extraction from pairing-capable sources (M2)"
python -m ingest.match_extract --cache data/MTGODecklistCache

echo "== rebuild complete"
