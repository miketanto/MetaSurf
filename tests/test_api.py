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


def test_events_credits_match_sources(client, seeded):
    body = client.get(f"{BASE}/events").json()
    assert "credits" in body
    feed_sources = {e["source"] for e in body["events"]}
    for c in body["credits"]:
        assert c["source"] in feed_sources  # never credit a source not shown
        assert c["url"] and c["attribution"]
    # required credits (if any) sort before optional ones
    reqs = [c["required"] for c in body["credits"]]
    assert reqs == sorted(reqs, reverse=True)


def test_credits_for_is_config_driven():
    from api.attribution import credits_for

    td = credits_for({"topdeck.gg"})
    assert len(td) == 1
    assert td[0].source == "topdeck.gg" and td[0].required is True
    assert td[0].attribution == "Data provided by TopDeck.gg"
    assert credits_for({"nonexistent-source"}) == []
    # required sources come first
    both = credits_for({"topdeck.gg", "mtgo.com"})
    assert [c.required for c in both] == sorted([c.required for c in both], reverse=True)


@pytest.fixture(scope="module")
def classify_client(seeded, test_db_url):
    """Client with the MTG classifier adapter injected, as serve.py wires it."""
    from archetypes.service import MtgClassifierService

    app = create_app(
        database_url_override=test_db_url, classifiers={GAME: MtgClassifierService()}
    )
    with TestClient(app) as c:
        yield c


def _deck_lines(conn, deck_id: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT c.name, dc.count, dc.board FROM deck_cards dc"
            " JOIN cards c ON c.id = dc.card_id WHERE dc.deck_id = %s"
            " ORDER BY dc.board, c.name",
            (deck_id,),
        )
        return [{"name": n, "count": ct, "board": b} for n, ct, b in cur.fetchall()]


def test_classify_requires_premium(classify_client):
    r = classify_client.post(
        f"{BASE}/classify", json={"cards": [{"name": "x", "count": 1, "board": "main"}]}
    )
    assert r.status_code == 403


def test_classify_501_when_no_adapter_wired(client):
    r = client.post(
        f"{BASE}/classify",
        json={"cards": [{"name": "x", "count": 1, "board": "main"}]},
        headers=PREMIUM_HEADERS,
    )
    assert r.status_code == 501


def test_classify_roundtrips_a_real_corpus_deck(classify_client, seeded):
    conn, _ = seeded
    top = classify_client.get(f"{BASE}/meta").json()["archetypes"][0]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT d.id FROM decks d WHERE d.archetype_id = %s ORDER BY d.id LIMIT 1",
            (top["archetype_id"],),
        )
        deck_id = cur.fetchone()[0]
    body = classify_client.post(
        f"{BASE}/classify", json={"cards": _deck_lines(conn, deck_id)}, headers=PREMIUM_HEADERS
    ).json()
    # the on-demand path must reproduce the batch label exactly
    assert body["archetype_id"] == top["archetype_id"]
    assert body["name"] == top["name"]
    assert body["method"] in {"rules", "fallback"}
    if body["method"] == "rules":
        assert body["confidence"] == 1.0
    else:
        assert 0.0 < body["confidence"] <= 1.0
    assert body["unresolved_cards"] == []
    # the top archetype is in the universe: spread + positioning score present
    assert body["as_of"] is not None
    assert body["matchup_spread"]
    for cell in body["matchup_spread"]:
        assert cell["ci_lo"] <= cell["p_win"] <= cell["ci_hi"]
        assert cell["name"]
    assert body["exp_winrate_vs_field"] is not None


def test_classify_reports_unresolved_never_guesses(classify_client, seeded):
    conn, _ = seeded
    with conn.cursor() as cur:
        cur.execute("SELECT c.name FROM deck_cards dc JOIN cards c ON c.id = dc.card_id LIMIT 1")
        real_name = cur.fetchone()[0]
    fake = "Zzyzx Imaginary Test Card"
    body = classify_client.post(
        f"{BASE}/classify",
        json={
            "cards": [
                {"name": fake, "count": 4, "board": "main"},
                {"name": real_name, "count": 4, "board": "main"},
            ]
        },
        headers=PREMIUM_HEADERS,
    ).json()
    assert body["unresolved_cards"] == [fake]


def test_classify_rejects_unknown_board_zone(classify_client):
    r = classify_client.post(
        f"{BASE}/classify",
        json={"cards": [{"name": "x", "count": 1, "board": "bench"}]},
        headers=PREMIUM_HEADERS,
    )
    assert r.status_code == 422


def test_trends_premium_gated_and_recomputable(client, seeded):
    conn, _ = seeded
    assert client.get(f"{BASE}/trends").status_code == 403

    body = client.get(f"{BASE}/trends", headers=PREMIUM_HEADERS).json()
    assert body["prev_week"] < body["week"]
    movers = body["movers"]
    assert movers
    deltas = [m["delta"] for m in movers]
    assert deltas == sorted(deltas, reverse=True)
    # recompute each delta from the stored weekly series
    with conn.cursor() as cur:
        cur.execute(
            "SELECT archetype_id, week, share FROM rollup_archetype_ts rt"
            " JOIN formats f ON f.id = rt.format_id AND f.name = %s"
            " WHERE week IN (%s, %s)",
            (FORMAT, body["week"], body["prev_week"]),
        )
        stored = {(a, w.isoformat()): s for a, w, s in cur.fetchall()}
    for m in movers:
        cur_share = stored.get((m["archetype_id"], body["week"]), 0.0)
        prev_share = stored.get((m["archetype_id"], body["prev_week"]), 0.0)
        assert m["share"] == pytest.approx(cur_share)
        assert m["delta"] == pytest.approx(cur_share - prev_share)


# ------------------------------------------------------------------ /emerging

# The 30-day default window has too few unlabeled fixture decks to cluster (see
# test_emerging.py); the endpoint contract is exercised with a wide window that
# yields real clusters. The builder is a game adapter, imported in the test.
EMERGING_WINDOW = 400


@pytest.fixture(scope="module")
def emerging_seeded(seeded):
    from archetypes.emerging import build_emerging as _build

    conn, as_of = seeded
    stats = _build(conn, GAME, FORMAT, as_of, window_days=EMERGING_WINDOW)
    assert stats.n_clusters > 0  # the fixture must surface >= 1 candidate
    return conn, as_of


def test_emerging_requires_premium(client, emerging_seeded):
    assert client.get(f"{BASE}/emerging").status_code == 403


def test_emerging_contract(client, emerging_seeded):
    conn, as_of = emerging_seeded
    body = client.get(f"{BASE}/emerging", headers=PREMIUM_HEADERS).json()
    assert body["game"] == GAME and body["format"] == FORMAT
    assert body["as_of"] == as_of.isoformat()
    clusters = body["clusters"]
    assert clusters

    # stored order: size desc, then first_seen, then cluster_key
    order = [(-c["n_decks"], c["first_seen"], c["cluster_key"]) for c in clusters]
    assert order == sorted(order)

    keys_seen = set()
    for c in clusters:
        keys_seen.add(c["cluster_key"])
        # never named here, and the descriptor is flagged unnamed (rule 4)
        assert c["named"] is False
        assert c["provisional_descriptor"].startswith("Unnamed:")
        assert c["n_decks"] >= 1
        assert 0 <= c["recent_decks"] <= c["n_decks"]
        if c["n_match_games"] == 0:
            assert c["winrate"] is None
        else:
            assert 0.0 <= c["winrate"] <= 1.0
        # signatures ranked by lift desc; each genuinely in > out of cluster
        lifts = [s["lift"] for s in c["signature_cards"]]
        assert lifts == sorted(lifts, reverse=True)
        for s in c["signature_cards"]:
            assert s["in_cluster_freq"] > s["out_cluster_freq"]
            assert s["name"]  # card name joined in
    assert len(keys_seen) == len(clusters)  # cluster_key unique in the snapshot

    # every row matches the stored rollup exactly (no per-request computation)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT cluster_key, provisional_descriptor, color, n_decks, first_seen,"
            " recent_decks, winrate, n_match_games FROM rollup_emerging"
            " JOIN formats f ON f.id = rollup_emerging.format_id AND f.name = %s"
            " WHERE as_of = %s ORDER BY n_decks DESC, first_seen, cluster_key",
            (FORMAT, as_of),
        )
        stored = cur.fetchall()
    assert len(stored) == len(clusters)
    for c, (key, desc, color, n, first, recent, wr, games) in zip(clusters, stored, strict=True):
        assert c["cluster_key"] == key
        assert c["provisional_descriptor"] == desc
        assert c["color"] == color
        assert c["n_decks"] == n
        assert c["first_seen"] == first.isoformat()
        assert c["recent_decks"] == recent
        assert c["n_match_games"] == games
        if wr is None:
            assert c["winrate"] is None
        else:
            assert c["winrate"] == pytest.approx(wr)


def test_emerging_empty_snapshot_is_ok(client, emerging_seeded):
    # a premium caller asking for a date with no clusters gets 200 + an empty
    # feed (absence of emerging decks is a valid answer), never 403 or 500
    resp = client.get(
        f"{BASE}/emerging", params={"as_of": "2016-01-01"}, headers=PREMIUM_HEADERS
    )
    assert resp.status_code == 200
    assert resp.json()["clusters"] == []


def test_serve_entrypoint_wires_classifier():
    import serve

    assert GAME in serve.app.state.classifiers


def test_emerging_build_entrypoint_wires_builder():
    # the build seam's composition root (outside the gated packages) wires an
    # EmergingBuilder adapter for the game, mirroring serve.py for classify
    from scripts.build_emerging import BUILDERS

    assert GAME in BUILDERS
    assert hasattr(BUILDERS[GAME], "build_emerging")


def test_openapi_spec_committed_and_current(client):
    committed = json.loads(Path("api/openapi.json").read_text())
    live = client.get("/openapi.json").json()
    assert committed == live, "api/openapi.json is stale; run python -m scripts.export_openapi"
