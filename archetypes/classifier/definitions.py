"""Loader for the ported MTGOFormatData rule files (archetypes/definitions/).

Rule files are data, ported unmodified (see archetypes/definitions/PROVENANCE.md).
Card names referenced by rules are resolved to cards.id at load time so that
rule matching operates on the same identity space as stored decks
(docs/notes/mtgoformatdata-observed-schema.md, port decision 2).

Name resolution order per rule name:
1. the caller-provided exact resolver (same one used for decklist ingestion);
2. an NFKD diacritic/whitespace/case fold, accepted only when it maps to
   exactly one card (observed upstream typos: a leading space and an
   ascii-for-û spelling; both unambiguous under the fold across all playable
   cards, and every fold use is reported to the caller — never silent).
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

DEFINITIONS_ROOT = Path(__file__).resolve().parent.parent / "definitions"

# Condition-type vocabulary of the reference implementation
# (MTGOArchetypeParser Model/ArchetypeConditionType.cs).
CONDITION_TYPES = frozenset(
    {
        "InMainboard",
        "InSideboard",
        "InMainOrSideboard",
        "OneOrMoreInMainboard",
        "OneOrMoreInSideboard",
        "OneOrMoreInMainOrSideboard",
        "TwoOrMoreInMainboard",
        "TwoOrMoreInSideboard",
        "TwoOrMoreInMainOrSideboard",
        "DoesNotContain",
        "DoesNotContainMainboard",
        "DoesNotContainSideboard",
    }
)


def fold_name(name: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch)
    ).casefold().strip()


@dataclass(frozen=True)
class Condition:
    type: str
    card_ids: tuple[int, ...]  # resolved; unresolved names are dropped + reported
    # names listed in the file. The reference skips conditions with an empty
    # Cards list; a *positive* condition whose names all failed to resolve is
    # NOT skipped — it can simply never match (raw_count distinguishes these).
    raw_count: int = 0


@dataclass(frozen=True)
class ArchetypeDef:
    name: str
    include_color_in_name: bool
    conditions: tuple[Condition, ...]
    variants: tuple[ArchetypeDef, ...] = ()


@dataclass(frozen=True)
class FallbackDef:
    name: str
    include_color_in_name: bool
    common_card_ids: tuple[int, ...]


@dataclass
class LoadReport:
    """Every non-exact or failed rule-name resolution, for audit."""

    fold_resolved: dict[str, int] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FormatDefinitions:
    format_name: str
    archetypes: tuple[ArchetypeDef, ...]
    fallbacks: tuple[FallbackDef, ...]
    # color identity tables, resolved to card ids (inert unresolved entries dropped)
    land_colors: dict[int, str]
    nonland_colors: dict[int, str]
    classifier_version: str


class _NameResolver:
    def __init__(
        self,
        resolve: Callable[[str], int | None],
        fold_index: dict[str, int | None],
        report: LoadReport,
    ):
        self._resolve = resolve
        self._fold_index = fold_index
        self._report = report

    def __call__(self, name: str) -> int | None:
        cid = self._resolve(name)
        if cid is not None:
            return cid
        folded = self._fold_index.get(fold_name(name))
        if folded is not None:
            self._report.fold_resolved[name] = folded
            return folded
        self._report.unresolved.append(name)
        return None


def build_fold_index(names_to_ids: Iterable[tuple[str, int]]) -> dict[str, int | None]:
    """foldkey -> card_id, or None where the fold is ambiguous (observed: 30
    ambiguous keys across playable cards; those must never fold-resolve)."""
    index: dict[str, int | None] = {}
    for name, cid in names_to_ids:
        key = fold_name(name)
        if key in index and index[key] != cid:
            index[key] = None
        else:
            index.setdefault(key, cid)
    return index


_TRAILING_COMMA = re.compile(r",(\s*[\]}])")


def _read_json(path: Path) -> dict:
    # Rule files have no BOM (observed), but utf-8-sig is harmless and robust.
    # Modern's color_overrides.json contains a trailing comma (observed),
    # which the reference's Newtonsoft.Json parser accepts — retry with
    # trailing commas stripped before failing.
    text = path.read_text(encoding="utf-8-sig")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = json.loads(_TRAILING_COMMA.sub(r"\1", text))
    assert isinstance(data, dict)
    return data


def _load_conditions(raw: dict, resolver: _NameResolver) -> tuple[Condition, ...]:
    out: list[Condition] = []
    for cond in raw.get("Conditions") or []:
        ctype = cond["Type"]
        if ctype not in CONDITION_TYPES:
            raise ValueError(f"unknown condition type {ctype!r}")
        names = cond.get("Cards") or []
        # reference behavior: single-card types only ever inspect Cards[0]
        if ctype.startswith(("In", "DoesNotContain")):
            names = names[:1]
        ids = tuple(cid for cid in (resolver(n) for n in names) if cid is not None)
        out.append(Condition(type=ctype, card_ids=ids, raw_count=len(names)))
    return tuple(out)


def _load_archetype(raw: dict, resolver: _NameResolver) -> ArchetypeDef:
    variants = tuple(
        _load_archetype(v, resolver) for v in raw.get("Variants") or []
    )
    return ArchetypeDef(
        name=raw["Name"],
        include_color_in_name=bool(raw.get("IncludeColorInName")),
        conditions=_load_conditions(raw, resolver),
        variants=variants,
    )


def compute_classifier_version(definition_files: list[Path], engine_semantics: str) -> str:
    h = hashlib.sha256()
    h.update(engine_semantics.encode())
    for path in sorted(definition_files):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return f"rules-{h.hexdigest()[:12]}"


def load_format(
    format_name: str,
    resolve: Callable[[str], int | None],
    fold_index: dict[str, int | None],
    engine_semantics: str,
    root: Path = DEFINITIONS_ROOT,
    report: LoadReport | None = None,
    exclude_file_stems: frozenset[str] = frozenset(),
) -> FormatDefinitions:
    """exclude_file_stems drops archetype FILES by stem (used by the V1.2
    emergence backtest to hide one definition). Exclusion is by file, not by
    Name: several files share a Name (observed: BassimAffinit.json also names
    itself 'Affinity'). The classifier_version hash covers only loaded files,
    so an exclusion yields a distinct version string."""
    report = report if report is not None else LoadReport()
    resolver = _NameResolver(resolve, fold_index, report)
    fmt_root = root / format_name

    archetype_files = [
        p
        for p in sorted((fmt_root / "Archetypes").glob("*.json"))
        if p.stem not in exclude_file_stems
    ]
    fallback_files = sorted((fmt_root / "Fallbacks").glob("*.json"))
    archetypes = tuple(_load_archetype(_read_json(p), resolver) for p in archetype_files)
    fallbacks = []
    for p in fallback_files:
        raw = _read_json(p)
        ids = tuple(
            cid
            for cid in (resolver(n) for n in raw.get("CommonCards") or [])
            if cid is not None
        )
        fallbacks.append(
            FallbackDef(
                name=raw["Name"],
                include_color_in_name=bool(raw.get("IncludeColorInName")),
                common_card_ids=ids,
            )
        )

    land_colors: dict[int, str] = {}
    nonland_colors: dict[int, str] = {}
    colors_raw = _read_json(root / "card_colors.json")
    overrides_path = fmt_root / "color_overrides.json"
    overrides = _read_json(overrides_path) if overrides_path.exists() else {}
    for source, target in (
        (colors_raw.get("Lands") or [], land_colors),
        (colors_raw.get("NonLands") or [], nonland_colors),
        (overrides.get("Lands") or [], land_colors),
        (overrides.get("NonLands") or [], nonland_colors),
    ):
        for entry in source:
            cid = resolve(entry["Name"])  # inert entries stay unresolved silently
            if cid is not None:
                target[cid] = entry["Color"]

    version = compute_classifier_version(
        archetype_files + fallback_files + [root / "card_colors.json"]
        + ([overrides_path] if overrides_path.exists() else []),
        engine_semantics,
    )
    return FormatDefinitions(
        format_name=format_name,
        archetypes=archetypes,
        fallbacks=tuple(fallbacks),
        land_colors=land_colors,
        nonland_colors=nonland_colors,
        classifier_version=version,
    )
