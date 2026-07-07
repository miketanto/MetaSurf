#!/usr/bin/env bash
# Fetch the two data prerequisites into data/ (both gitignored).
#   - MTGODecklistCache: frozen archive, cloned once, treated as read-only
#   - Scryfall oracle-cards bulk file (cached locally per Scryfall guidance)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/scryfall

if [ ! -d data/MTGODecklistCache ]; then
    echo "== cloning MTGODecklistCache (frozen archive)"
    git clone --depth 1 https://github.com/Badaro/MTGODecklistCache.git data/MTGODecklistCache
else
    echo "== data/MTGODecklistCache already present (frozen; not pulling)"
fi

if [ ! -f data/scryfall/oracle-cards.json ]; then
    echo "== fetching Scryfall oracle-cards bulk data"
    UA="metagame-platform/0.1 (research; contact: repo owner)"
    URI=$(curl -fsS -A "$UA" https://api.scryfall.com/bulk-data \
        | python3 -c "import json,sys; d=json.load(sys.stdin); \
print(next(x['download_uri'] for x in d['data'] if x['type']=='oracle_cards'))")
    echo "   $URI"
    curl -fsS -A "$UA" -o data/scryfall/oracle-cards.json "$URI"
    ls -la data/scryfall/oracle-cards.json
else
    echo "== data/scryfall/oracle-cards.json already present"
fi
