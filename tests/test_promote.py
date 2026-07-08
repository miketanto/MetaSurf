"""Promote-to-rule helper: scaffold a rule file from an emerging cluster and
verify the loop closes — a *named* scaffold, loaded by the same rules engine,
classifies the cluster's own decks deterministically.

Runs against the real fixture corpus (like test_emerging.py). No fabricated
values: the scaffold's key cards are the cluster's own signature cards, and the
loop test loads them through the production loader.
"""

from __future__ import annotations

import datetime as dt
import shutil

import orjson
import psycopg
import pytest

from archetypes.classifier.corpus import load_decks
from archetypes.classifier.definitions import DEFINITIONS_ROOT, build_fold_index, load_format
from archetypes.classifier.engine import ENGINE_SEMANTICS, classify
from archetypes.emerging import build_emerging, characterize
from archetypes.labeler import label_corpus
from archetypes.promote import (
    NAME_PLACEHOLDER,
    assert_named,
    is_named,
    scaffold_from_cluster,
    scaffold_from_rollup,
)
from ingest.cache_import.importer import run_import
from ingest.match_extract import extract_matches
from ingest.normalize.resolver import CardResolver
from tests.conftest import FIXTURES

pytestmark = pytest.mark.db

GAME = "mtg"
FORMAT = "modern"
WINDOW = 400


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
def corpus_conn(test_db_url):
    conn = psycopg.connect(test_db_url)
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE rollup_emerging_signature, rollup_emerging, ingest_unresolved_cards,"
            " archetype_labels, matches, deck_cards, decks, events, archetypes, cards"
            " RESTART IDENTITY CASCADE"
        )
        cur.execute("INSERT INTO games (name) VALUES ('mtg') ON CONFLICT DO NOTHING")
        cur.execute("SELECT id FROM games WHERE name = 'mtg'")
        game_id = cur.fetchone()[0]
        cur.executemany(
            "INSERT INTO cards (game_id, canonical_ref, name) VALUES (%s, %s, %s)",
            [(game_id, f"test-ref:{i}", n) for i, n in enumerate(sorted(_fixture_card_names()))],
        )
    conn.commit()
    run_import(conn, FIXTURES)
    label_corpus(conn)
    extract_matches(conn, FIXTURES)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def as_of(corpus_conn) -> dt.date:
    with corpus_conn.cursor() as cur:
        cur.execute("SELECT max(date) FROM events")
        return cur.fetchone()[0]


@pytest.fixture(scope="module")
def top_cluster(corpus_conn, as_of):
    clusters = characterize(corpus_conn, FORMAT, as_of, window_days=WINDOW)
    assert clusters
    return clusters[0]


def test_scaffold_is_unnamed_and_has_key_conditions(corpus_conn, top_cluster):
    scaffold = scaffold_from_cluster(corpus_conn, top_cluster)
    # never auto-named (CLAUDE.md rule 4)
    assert scaffold["Name"] == NAME_PLACEHOLDER
    assert not is_named(scaffold)
    with pytest.raises(ValueError):
        assert_named(scaffold)
    # key-card conditions come from the cluster's signature cards
    assert scaffold["Conditions"], "a cluster with signatures scaffolds conditions"
    for cond in scaffold["Conditions"]:
        assert cond["Type"] == "InMainboard"
        assert len(cond["Cards"]) == 1 and cond["Cards"][0]
    sig_names = {
        _name(corpus_conn, s.card_id) for s in top_cluster.signature_cards
    }
    for cond in scaffold["Conditions"]:
        assert cond["Cards"][0] in sig_names


def test_naming_the_scaffold_passes_the_guard(corpus_conn, top_cluster):
    scaffold = scaffold_from_cluster(corpus_conn, top_cluster)
    scaffold["Name"] = "SomeHumanChosenName"
    assert is_named(scaffold)
    assert_named(scaffold)  # no raise


def test_rollup_and_memory_scaffolds_agree(corpus_conn, as_of, top_cluster):
    build_emerging(corpus_conn, GAME, FORMAT, as_of, window_days=WINDOW)
    from_mem = scaffold_from_cluster(corpus_conn, top_cluster)
    from_db = scaffold_from_rollup(corpus_conn, GAME, FORMAT, as_of, top_cluster.cluster_key)
    assert from_db["Conditions"] == from_mem["Conditions"]


def test_promoted_rule_closes_the_loop(corpus_conn, as_of, top_cluster, tmp_path):
    """A named scaffold, loaded by the production rules engine, classifies the
    cluster's own decks under that name — the emerging loop closed."""
    scaffold = scaffold_from_cluster(corpus_conn, top_cluster)
    scaffold["Name"] = "EmergingUnderTest"
    assert_named(scaffold)

    # a throwaway definitions root = the format's real files + the new rule
    root = tmp_path / "defs"
    shutil.copytree(DEFINITIONS_ROOT, root)
    clean = {k: v for k, v in scaffold.items() if not k.startswith("_")}
    (root / FORMAT / "Archetypes" / "EmergingUnderTest.json").write_text(
        orjson.dumps(clean, option=orjson.OPT_INDENT_2).decode()
    )

    resolver = CardResolver.from_db(corpus_conn, GAME)
    with corpus_conn.cursor() as cur:
        cur.execute(
            "SELECT c.name, c.id FROM cards c JOIN games g ON g.id = c.game_id"
            " WHERE g.name = 'mtg' ORDER BY c.id"
        )
        fold_index = build_fold_index(cur.fetchall())
    defs = load_format(FORMAT, resolver.resolve, fold_index, ENGINE_SEMANTICS, root=root)

    # the cluster's decks now classify under the promoted rule
    first = as_of - dt.timedelta(days=WINDOW)
    by_id = {d.deck_id: d for d in load_decks(corpus_conn, first, as_of, FORMAT)}
    hits = 0
    for did in top_cluster.deck_ids:
        res = classify(by_id[did].deck, defs)
        if res.match is not None and res.match.archetype == "EmergingUnderTest":
            hits += 1
    # the scaffold is built from the cluster's own key cards, so it must catch a
    # clear majority of the cluster it came from
    assert hits / len(top_cluster.deck_ids) >= 0.5


def _name(conn: psycopg.Connection, card_id: int) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM cards WHERE id = %s", (card_id,))
        return cur.fetchone()[0]


def test_scaffold_from_rollup_unknown_cluster_raises(corpus_conn, as_of):
    build_emerging(corpus_conn, GAME, FORMAT, as_of, window_days=WINDOW)
    with pytest.raises(LookupError):
        scaffold_from_rollup(corpus_conn, GAME, FORMAT, as_of, cluster_key=999999)
