"""Rules-stage classifier: reference-parity reimplementation of
MTGOArchetypeParser's ArchetypeAnalyzer (see
docs/notes/mtgoformatdata-observed-schema.md for the semantics, quoted from
the C# source at the pinned commit). Operates on cards.id vectors, the same
identity space as stored decks.

Deterministic by construction: no randomness, dict/tuple iteration in file
order, conflicts resolved PreferSimpler (fewest conditions) with the full
conflict set reported for audit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from archetypes.classifier.definitions import (
    ArchetypeDef,
    Condition,
    FallbackDef,
    FormatDefinitions,
)

ENGINE_SEMANTICS = "mtgoarchetypeparser-parity-1"

# reference: GetBestGenericArchetype minSimiliarity default
MIN_FALLBACK_SIMILARITY = 0.1

# verbatim from the reference GetColorName switch (Model/Archetype.cs);
# colors not listed (incl. 'C') hit the default and prefix nothing
_GUILD_NAMES = {
    "W": "MonoWhite", "U": "MonoBlue", "B": "MonoBlack", "R": "MonoRed", "G": "MonoGreen",
    "WU": "Azorius", "WB": "Orzhov", "WR": "Boros", "WG": "Selesnya",
    "UB": "Dimir", "UR": "Izzet", "UG": "Simic",
    "BR": "Rakdos", "BG": "Golgari", "RG": "Gruul",
    "WUB": "Esper", "WUR": "Jeskai", "WUG": "Bant",
    "WBR": "Mardu", "WBG": "Abzan", "WRG": "Naya",
    "UBR": "Grixis", "UBG": "Sultai", "URG": "Temur",
    "BRG": "Jund",
    "WUBR": "WUBR", "WBRG": "WBRG", "WUBG": "WUBG", "WURG": "WURG", "UBRG": "UBRG",
    "WUBRG": "5Color",
}

_PASCAL_SPLIT = re.compile(
    r"(?<=[A-Z])(?=[A-Z][a-z])|(?<=[^A-Z])(?=[A-Z])|(?<=[A-Za-z])(?=[^A-Za-z])"
)


@dataclass(frozen=True)
class Deck:
    """Card-id -> count per zone (from deck_cards: board 'main'/'side')."""

    main: dict[int, int]
    side: dict[int, int]


@dataclass(frozen=True)
class Match:
    archetype: str
    variant: str | None
    label: str  # display name incl. color prefixing, reference GetName()
    method: str  # 'rules' | 'fallback'
    similarity: float  # 1.0 for rules matches


@dataclass(frozen=True)
class Classification:
    match: Match | None  # None = unclassified by rules stage
    color: str
    conflict: tuple[str, ...] = ()  # labels of all specific matches when >1


def _display_name(raw_name: str, include_color: bool, color: str) -> str:
    name = raw_name.replace("Generic", "")
    if include_color:
        name = _GUILD_NAMES.get(color, "") + name
    name = _PASCAL_SPLIT.sub(" ", name)
    return re.sub(r"\s+", " ", name).strip()


def _condition_holds(cond: Condition, deck: Deck) -> bool:
    if cond.raw_count == 0:  # reference: skips broken (empty-Cards) conditions
        return True
    ids = cond.card_ids
    in_main = sum(1 for cid in ids if cid in deck.main)
    in_side = sum(1 for cid in ids if cid in deck.side)
    t = cond.type
    if t == "InMainboard" or t == "OneOrMoreInMainboard":
        return in_main >= 1
    if t == "InSideboard" or t == "OneOrMoreInSideboard":
        return in_side >= 1
    if t == "InMainOrSideboard" or t == "OneOrMoreInMainOrSideboard":
        return in_main >= 1 or in_side >= 1
    if t == "TwoOrMoreInMainboard":
        return in_main >= 2
    if t == "TwoOrMoreInSideboard":
        return in_side >= 2
    if t == "TwoOrMoreInMainOrSideboard":
        return in_main + in_side >= 2
    if t == "DoesNotContain":
        return in_main == 0 and in_side == 0
    if t == "DoesNotContainMainboard":
        return in_main == 0
    if t == "DoesNotContainSideboard":
        return in_side == 0
    raise ValueError(f"unknown condition type {t!r}")


def _matches(archetype: ArchetypeDef, deck: Deck) -> bool:
    return all(_condition_holds(c, deck) for c in archetype.conditions)


def deck_color(deck: Deck, defs: FormatDefinitions) -> str:
    """Reference GetColors: a color counts iff present (copy-weighted) in both
    a land and a non-land across main+side."""
    in_lands = dict.fromkeys("WUBRG", 0)
    in_nonlands = dict.fromkeys("WUBRG", 0)
    for zone in (deck.main, deck.side):
        for cid, count in zone.items():
            for ch in defs.land_colors.get(cid, ""):
                in_lands[ch] += count
            for ch in defs.nonland_colors.get(cid, ""):
                in_nonlands[ch] += count
    color = "".join(ch for ch in "WUBRG" if in_lands[ch] > 0 and in_nonlands[ch] > 0)
    return color or "C"


def _best_fallback(
    deck: Deck, fallbacks: tuple[FallbackDef, ...]
) -> tuple[FallbackDef, float] | None:
    """Reference GetBestGenericArchetype: weight = copies of distinct present
    common cards; similarity = weight / distinct deck entries (main+side)."""
    weights: list[tuple[FallbackDef, int]] = []
    for fb in fallbacks:
        common = set(fb.common_card_ids)
        weight = sum(
            count
            for cid, count in list(deck.main.items()) + list(deck.side.items())
            if cid in common
        )
        weights.append((fb, weight))
    if all(w == 0 for _, w in weights):
        return None
    max_w = max(w for _, w in weights)
    best = min(
        (fb for fb, w in weights if w == max_w),
        key=lambda fb: len(fb.common_card_ids),
    )
    entries = len(deck.main) + len(deck.side)
    return best, (max_w / entries if entries else 0.0)


def classify(deck: Deck, defs: FormatDefinitions) -> Classification:
    color = deck_color(deck, defs)

    results: list[tuple[ArchetypeDef, ArchetypeDef | None]] = []
    for archetype in defs.archetypes:
        if not _matches(archetype, deck):
            continue
        matched_variants = [v for v in archetype.variants if _matches(v, deck)]
        if matched_variants:
            results.extend((archetype, v) for v in matched_variants)
        else:
            results.append((archetype, None))

    if results:
        conflict: tuple[str, ...] = ()
        if len(results) > 1:
            conflict = tuple(
                _display_name(
                    (v or a).name, (v or a).include_color_in_name, color
                )
                for a, v in results
            )
            # reference ConflictSolvingMode.PreferSimpler
            results.sort(
                key=lambda av: len(av[0].conditions)
                + (len(av[1].conditions) if av[1] else 0)
            )
            results = results[:1]
        archetype, variant = results[0]
        named = variant or archetype
        return Classification(
            match=Match(
                archetype=archetype.name,
                variant=variant.name if variant else None,
                label=_display_name(named.name, named.include_color_in_name, color),
                method="rules",
                similarity=1.0,
            ),
            color=color,
            conflict=conflict,
        )

    fallback = _best_fallback(deck, defs.fallbacks)
    if fallback is not None:
        fb, similarity = fallback
        if similarity > MIN_FALLBACK_SIMILARITY:
            return Classification(
                match=Match(
                    archetype=fb.name,
                    variant=None,
                    label=_display_name(fb.name, fb.include_color_in_name, color),
                    method="fallback",
                    similarity=similarity,
                ),
                color=color,
            )
    return Classification(match=None, color=color)
