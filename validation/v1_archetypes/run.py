"""V1.1-V1.3 validation suites (plan §5 Layer 1). Every number in the emitted
report is computed here at run time; the full run executes twice and the
metrics blocks must be byte-identical (V1.3).

Methodology (documented in the report as well):

V1.1 — hold-out month. Ground truth = specific-rules labels (method='rules',
no conflict) from the ported definitions. The clustering stage runs
unsupervised on ALL decks of the month; each cluster is mapped to its
majority rule label; predicted label for a deck = its cluster's mapped label
(noise/Rogue predicts nothing). Established archetypes = rule labels with
>= 50 decks in the month. Agreement = fraction of established-label decks
whose predicted label equals their rule label. Per-archetype P/R/F1 over the
mapped predictions; ARI between cluster ids and rule labels on rules-labeled
decks.

V1.2 — emergence backtest. For each historical event (a genuinely new deck,
identified by a key card observed in the corpus), the target archetype's rule
file is removed from the definitions ("the world before the deck was named");
each day from the deck's first appearance we cluster the rules-unlabeled
remainder accumulated since a window start; the event passes if within 7 days
of the first date with >= 5 cumulative appearances there is a cluster of
>= 5 decks whose majority are the target archetype's decks per today's rules.

V1.3 — determinism: the full V1.1 + V1.2 computation runs twice in-process;
their serialized metrics must be byte-identical.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import Any

import psycopg
from sklearn.metrics import adjusted_rand_score

from archetypes.classifier.clustering import NOISE, cluster_and_attach
from archetypes.classifier.engine import Classification
from archetypes.classifier.vectorizer import vectorize
from validation.v1_archetypes.common import (
    LoadedDeck,
    basic_land_ids,
    load_decks,
    load_definitions,
    rules_label,
)

HOLDOUT_START = dt.date(2024, 1, 1)  # highest-volume month in the corpus
HOLDOUT_END = dt.date(2024, 1, 31)
ESTABLISHED_MIN_DECKS = 50
MAJOR_F1_TARGET = 0.90
AGREEMENT_TARGET = 0.95

# Emergence events: (label, archetype rule FILE stem, key card, window start).
# Both chosen from executed corpus queries (see the report): the key card's
# daily deck counts identify the deck's real arrival. Exclusion is by file
# stem because rule Names are not unique (BassimAffinit.json names itself
# 'Affinity'); the target deck set is keyed by the new card itself.
EMERGENCE_EVENTS = (
    ("MH3 release — Nadu", "Nadu", "Nadu, Winged Wisdom", dt.date(2024, 6, 1)),
    (
        "Assassin's Creed release — Basim",
        "BassimAffinit",
        "Basim Ibn Ishaq",
        dt.date(2024, 7, 1),
    ),
)
EMERGENCE_HORIZON_DAYS = 7
EMERGENCE_MIN_APPEARANCES = 5


def _rule_truth(
    decks: list[LoadedDeck], classifications: list[Classification]
) -> dict[int, str]:
    """deck_id -> archetype name for specific-rules matches without conflict."""
    truth: dict[int, str] = {}
    for d, c in zip(decks, classifications, strict=True):
        if c.match is not None and c.match.method == "rules" and not c.conflict:
            truth[d.deck_id] = c.match.archetype
    return truth


def run_v11(
    conn: psycopg.Connection,
    format_name: str = "modern",
    holdout_start: dt.date = HOLDOUT_START,
    holdout_end: dt.date = HOLDOUT_END,
    rules_dir: str | None = None,
) -> dict[str, Any]:
    # rules_dir lets a rotating-format holdout validate against the era-matched
    # rule set current at the holdout date, not today's post-rotation rules.
    defs, load_report = load_definitions(conn, format_name=rules_dir or format_name)
    decks = load_decks(conn, holdout_start, holdout_end, format_name)
    classifications = rules_label(decks, defs)
    truth = _rule_truth(decks, classifications)

    exclude = basic_land_ids(conn)
    vectors = vectorize([(d.deck_id, d.deck.main) for d in decks], exclude)
    labels = cluster_and_attach(vectors.matrix)

    by_label = Counter(truth.values())
    established = {a for a, n in by_label.items() if n >= ESTABLISHED_MIN_DECKS}

    # majority-label mapping per cluster
    cluster_members: dict[int, list[int]] = defaultdict(list)
    for deck_id, cl in zip(vectors.deck_ids, labels, strict=True):
        cluster_members[int(cl)].append(deck_id)
    mapped: dict[int, str | None] = {}
    for cl, members in cluster_members.items():
        if cl == NOISE:
            continue
        votes = Counter(truth[m] for m in members if m in truth)
        mapped[cl] = min(
            (name for name, v in votes.items() if v == votes.most_common(1)[0][1]),
            default=None,
        )

    predicted: dict[int, str | None] = {}
    for deck_id, cl in zip(vectors.deck_ids, labels, strict=True):
        predicted[deck_id] = mapped.get(int(cl))

    # agreement over established-truth decks
    est_decks = [d for d in truth if truth[d] in established]
    agree = sum(1 for d in est_decks if predicted.get(d) == truth[d])
    agreement = agree / len(est_decks) if est_decks else 0.0

    # per-archetype P/R/F1 (established only)
    per_arch: list[tuple[str, int, float, float, float]] = []
    for arch in sorted(established):
        tp = sum(1 for d in truth if truth[d] == arch and predicted.get(d) == arch)
        fp = sum(1 for d in truth if truth[d] != arch and predicted.get(d) == arch)
        fn = sum(1 for d in truth if truth[d] == arch and predicted.get(d) != arch)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        per_arch.append((arch, by_label[arch], p, r, f1))

    labeled_ids = [d for d in vectors.deck_ids if d in truth]
    cl_of = dict(zip(vectors.deck_ids, labels, strict=True))
    ari = adjusted_rand_score(
        [truth[d] for d in labeled_ids], [int(cl_of[d]) for d in labeled_ids]
    )

    n_clusters = len([c for c in cluster_members if c != NOISE])
    noise = len(cluster_members.get(NOISE, []))
    return {
        "decks": len(decks),
        "rules_labeled": len(truth),
        "conflicts": sum(1 for c in classifications if c.conflict),
        "fallback_labeled": sum(
            1
            for c in classifications
            if c.match is not None and c.match.method == "fallback"
        ),
        "established": sorted(established),
        "clusters": n_clusters,
        "noise": noise,
        "agreement": agreement,
        "per_archetype": per_arch,
        "ari": ari,
        "classifier_version": defs.classifier_version,
        "fold_resolved": sorted(load_report.fold_resolved),
        "unresolved_rule_names": sorted(load_report.unresolved),
    }


def run_v12(
    conn: psycopg.Connection,
    format_name: str = "modern",
    emergence_events: tuple[tuple[str, str, str, dt.date], ...] = EMERGENCE_EVENTS,
) -> list[dict[str, Any]]:
    # emergence events are format-specific (chosen from that format's corpus);
    # a format with none defined simply has no V1.2 to run.
    if not emergence_events:
        return []
    results: list[dict[str, Any]] = []
    full_defs, _ = load_definitions(conn, format_name=format_name)
    exclude = basic_land_ids(conn)
    for label, file_stem, key_card, window_start in emergence_events:
        blind_defs, _ = load_definitions(
            conn, frozenset({file_stem}), format_name=format_name
        )
        assert len(blind_defs.archetypes) == len(full_defs.archetypes) - 1

        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.id FROM cards c JOIN games g ON g.id = c.game_id"
                " WHERE g.name = 'mtg' AND c.name = %s",
                (key_card,),
            )
            row = cur.fetchone()
            assert row is not None, key_card
            key_id = row[0]

        decks = load_decks(
            conn, window_start, window_start + dt.timedelta(days=60), format_name
        )
        # "the new deck" = decks playing the new key card in the mainboard
        target_ids = {d.deck_id for d in decks if key_id in d.deck.main}
        # first date with cumulative >= EMERGENCE_MIN_APPEARANCES target decks
        dates = sorted(d.event_date for d in decks if d.deck_id in target_ids)
        if len(dates) < EMERGENCE_MIN_APPEARANCES:
            results.append(
                {"event": label, "error": f"only {len(dates)} target decks in window"}
            )
            continue
        first5 = dates[EMERGENCE_MIN_APPEARANCES - 1]
        deadline = first5 + dt.timedelta(days=EMERGENCE_HORIZON_DAYS)

        blind = rules_label(decks, blind_defs)
        remainder = [
            d
            for d, c in zip(decks, blind, strict=True)
            if not (c.match is not None and c.match.method == "rules")
        ]

        detected_on: dt.date | None = None
        detected_size = 0
        detected_purity = 0.0
        day = first5
        while day <= deadline:
            window = [d for d in remainder if d.event_date <= day]
            if len(window) >= EMERGENCE_MIN_APPEARANCES:
                vectors = vectorize([(d.deck_id, d.deck.main) for d in window], exclude)
                labels = cluster_and_attach(vectors.matrix)
                members: dict[int, list[int]] = defaultdict(list)
                for deck_id, cl in zip(vectors.deck_ids, labels, strict=True):
                    if int(cl) != NOISE:
                        members[int(cl)].append(deck_id)
                for _cl, ids in sorted(members.items()):
                    hits = sum(1 for i in ids if i in target_ids)
                    if len(ids) >= EMERGENCE_MIN_APPEARANCES and hits / len(ids) > 0.5:
                        detected_on = day
                        detected_size = len(ids)
                        detected_purity = hits / len(ids)
                        break
            if detected_on:
                break
            day += dt.timedelta(days=1)

        results.append(
            {
                "event": label,
                "archetype": file_stem,
                "key_card": key_card,
                "target_decks_in_window": len(target_ids),
                "first_5_appearances": first5.isoformat(),
                "deadline": deadline.isoformat(),
                "detected_on": detected_on.isoformat() if detected_on else None,
                "detected_cluster_size": detected_size,
                "detected_cluster_purity": round(detected_purity, 4),
                "passed": detected_on is not None,
            }
        )
    return results


def format_metrics(v11: dict, v12: list[dict]) -> str:
    """Deterministic serialization compared byte-for-byte across runs (V1.3)."""
    lines = [
        f"decks={v11['decks']} rules_labeled={v11['rules_labeled']}"
        f" conflicts={v11['conflicts']} fallback={v11['fallback_labeled']}",
        f"clusters={v11['clusters']} noise={v11['noise']}"
        f" agreement={v11['agreement']:.6f} ari={v11['ari']:.6f}",
    ]
    for arch, n, p, r, f1 in v11["per_archetype"]:
        lines.append(f"{arch} n={n} p={p:.6f} r={r:.6f} f1={f1:.6f}")
    for ev in v12:
        lines.append(str(sorted(ev.items())))
    return "\n".join(lines)
