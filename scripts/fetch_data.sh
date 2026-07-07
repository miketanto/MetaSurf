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

if [ -f data/scryfall/oracle-cards.jsonl ] || [ -f data/scryfall/oracle-cards.json ]; then
    echo "== Scryfall oracle-cards bulk data already present"
else
    echo "== fetching Scryfall oracle-cards bulk data"
    UA="metagame-platform/0.1 (research; contact: repo owner)"
    # Prefer the JSONL framing (per Scryfall's July 2026 API notes the array
    # framing retires 2026-07-20); fall back to download_uri for older mirrors.
    URI=$(curl -fsS -A "$UA" https://api.scryfall.com/bulk-data \
        | python3 -c "import json,sys; d=json.load(sys.stdin); \
o=next(x for x in d['data'] if x['type']=='oracle_cards'); \
print(o.get('jsonl_download_uri') or o['download_uri'])")
    echo "   $URI"
    case "$URI" in
        *.jsonl*) OUT=data/scryfall/oracle-cards.jsonl ;;
        *)        OUT=data/scryfall/oracle-cards.json ;;
    esac
    curl -fsS -A "$UA" -o "$OUT" "$URI"
    ls -la "$OUT"
fi
