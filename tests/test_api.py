"""Read-API contract tests against rollups built from the real fixture corpus.

The rollup numbers themselves are covered by test_rollup_jobs.py; these
tests pin the client contract: response shapes, ordering, 404 semantics,
tier gating through the entitlements module, and that the committed OpenAPI
spec matches the app.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import orjson
import psycopg
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from archetypes.labeler import label_corpus
from ingest.cache_import.importer import run_import
from ingest.match_extract import extract_matches
from jobs.rollups import (
    build_archetype_ts,
    build_best_decks,
    build_events,
    build_matchups,
    build_meta,
)
from tests.conftest import FIXTURES

pytestmark = pytest.mark.db

GAME = "mtg"
FORMAT = "modern"
BASE = f"/v1/{GAME}/{FORMAT}"
PREMIUM_HEADERS = {"X-Entitlements": "premium"}


def _fixture_card_names() -> set[str]:
    names: set[str] = set()
    for path in sorted((FIXTURES / "Tournaments").glob("*/*/*/*/*.json")):
        data = orjson.loads(path.read_bytes())
        for deck in data.get("Decks") or []:
            for zone in ("Mainboard", "Sideboard"):
                for entry in deck.get(zone) or []:
                    names.add(entry["CardName"])
    return names


@pytest.fixture(scope="module")
def seeded(test_db_url):
    """Fixture corpus imported, labeled, match-extracted, and rolled up."""
    conn = psycopg.connect(test_db_url)
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE rollup_meta, rollup_matchups, rollup_archetype_ts, rollup_best_decks,"
            " rollup_events, ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
            " decks, events, archetypes, cards RESTART IDENTITY CASCADE"
        )
        cur.execute("INSERT INTO games (name) VALUES ('mtg') ON CONFLICT DO NOTHING")
        cur.execute("SELECT id FROM games WHERE name = 'mtg'")
        game_id = cur.fetchone()[0]
        names = sorted(_fixture_card_names())
        cur.executemany(
            "INSERT INTO cards (game_id, canonical_ref, name) VALUES (%s, %s, %s)",
            [(game_id, f"test-ref:{i}", n) for i, n in enumerate(names)],
        )
    conn.commit()
    run_import(conn, FIXTURES)
    label_corpus(conn)
    extract_matches(conn, FIXTURES)
    with conn.cursor() as cur:
        cur.execute("SELECT max(date) FROM events")
        as_of = cur.fetchone()[0]
    for job in (build_meta, build_matchups, build_best_decks, build_archetype_ts, build_events):
        job(conn, GAME, FORMAT, as_of)
    yield conn, as_of
    conn.close()


@pytest.fixture(scope="module")
def client(seeded, test_db_url):
    with TestClient(create_app(database_url_override=test_db_url)) as c:
        yield c


def test_meta_contract(client, seeded):
    _, as_of = seeded
    body = client.get(f"{BASE}/meta").json()
    assert body["game"] == GAME and body["format"] == FORMAT
    assert body["as_of"] == as_of.isoformat()
    archetypes = body["archetypes"]
    assert archetypes
    shares = [a["share"] for a in archetypes]
    assert shares == sorted(shares, reverse=True)
    assert sum(shares) == pytest.approx(1.0)
    for a in archetypes:
        assert set(a) == {
            "archetype_id", "name", "share", "winrate",
            "wr_ci_lo", "wr_ci_hi", "n_decks", "sparkline",
        }
        assert a["name"]
        assert a["wr_ci_lo"] <= a["winrate"] <= a["wr_ci_hi"]
        assert a["sparkline"] and all(0.0 <= s <= 1.0 for s in a["sparkline"])


def test_meta_as_of_param_and_404s(client, seeded):
    _, as_of = seeded
    assert client.get(f"{BASE}/meta", params={"as_of": as_of.isoformat()}).status_code == 200
    assert client.get(f"{BASE}/meta", params={"as_of": "2010-01-01"}).status_code == 404
    assert client.get(f"/v1/no-such-game/{FORMAT}/meta").status_code == 404
    assert client.get(f"/v1/{GAME}/no-such-format/meta").status_code == 404


def test_matchups_contract(client):
    body = client.get(f"{BASE}/matchups").json()
    axis = [a["archetype_id"] for a in body["archetypes"]]
    assert len(axis) >= 2 and all(a["name"] for a in body["archetypes"])
    cells = body["cells"]
    assert len(cells) == len(axis) ** 2
    p = {(c["arch_a"], c["arch_b"]): c["p_a_beats_b"] for c in cells}
    for c in cells:
        assert c["ci_lo"] <= c["p_a_beats_b"] <= c["ci_hi"]
        assert c["n_matches"] >= 0
        assert p[c["arch_a"], c["arch_b"]] + p[c["arch_b"], c["arch_a"]] == pytest.approx(1.0)


def test_matchup_detail_tier_gating(client):
    axis = [a["archetype_id"] for a in client.get(f"{BASE}/matchups").json()["archetypes"]]
    a, b = axis[0], axis[1]

    free = client.get(f"{BASE}/matchups/{a}/{b}").json()
    assert free["history"] is None and free["history_locked"] is True
    assert free["trend"] is None  # single snapshot on the frozen corpus
    assert free["ci_lo"] <= free["p_a_beats_b"] <= free["ci_hi"]
    assert free["arch_a"]["archetype_id"] == a and free["arch_b"]["archetype_id"] == b

    paid = client.get(f"{BASE}/matchups/{a}/{b}", headers=PREMIUM_HEADERS).json()
    assert paid["history_locked"] is False
    assert [h["as_of"] for h in paid["history"]] == [paid["as_of"]]
    assert paid["history"][-1]["p_a_beats_b"] == free["p_a_beats_b"]

    assert client.get(f"{BASE}/matchups/999998/999999").status_code == 404


def test_best_decks_contract(client):
    body = client.get(f"{BASE}/best-decks").json()
    decks = body["decks"]
    assert decks
    assert [d["rank"] for d in decks] == list(range(1, len(decks) + 1))
    scores = [d["exp_winrate_vs_field"] for d in decks]
    assert scores == sorted(scores, reverse=True)
    assert all(d["name"] and 0.0 < d["exp_winrate_vs_field"] < 1.0 for d in decks)


def test_archetype_detail_tier_gating(client, seeded):
    _, as_of = seeded
    top = client.get(f"{BASE}/meta").json()["archetypes"][0]
    arch = top["archetype_id"]

    free = client.get(f"{BASE}/archetypes/{arch}").json()
    assert free["series"] is None and free["series_locked"] is True
    assert free["share"] == top["share"] and free["name"] == top["name"]

    paid = client.get(
        f"{BASE}/archetypes/{arch}", params={"weeks": 52}, headers=PREMIUM_HEADERS
    ).json()
    assert paid["series_locked"] is False
    series = paid["series"]
    assert series
    weeks = [p["week"] for p in series]
    assert weeks == sorted(weeks)
    assert dt.date.fromisoformat(weeks[-1]) <= as_of
    for point in series:
        if point["n_decks"] == 0:  # zero-filled data week
            assert point["share"] == 0.0 and point["winrate"] is None
        else:
            assert point["wr_ci_lo"] <= point["winrate"] <= point["wr_ci_hi"]

    assert client.get(f"{BASE}/archetypes/999999").status_code == 404


def test_events_contract(client, seeded):
    conn, as_of = seeded
    body = client.get(f"{BASE}/events").json()
    events = body["events"]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM events e JOIN formats f ON f.id = e.format_id"
            " WHERE f.name = %s AND e.date <= %s",
            (FORMAT, as_of),
        )
        expected = cur.fetchone()[0]
    assert len(events) == expected > 0
    dates = [e["date"] for e in events]
    assert dates == sorted(dates, reverse=True)
    for e in events:
        assert e["source"]
        assert (e["top_archetype"] is None) == (e["top_archetype_id"] is None)

    assert len(client.get(f"{BASE}/events", params={"limit": 3}).json()["events"]) == 3


def test_openapi_spec_committed_and_current(client):
    committed = json.loads(Path("api/openapi.json").read_text())
    live = client.get("/openapi.json").json()
    assert committed == live, "api/openapi.json is stale; run python -m scripts.export_openapi"
