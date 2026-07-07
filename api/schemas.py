"""Response models — the read API's client contract (versioned under /v1).

Premium sections are present in every response shape with a ``*_locked``
flag: free callers see the field name and that it's locked, never the data
(plan §8: the freemium line runs through the screen, not around it).
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class MetaArchetype(BaseModel):
    archetype_id: int
    name: str
    share: float
    winrate: float
    wr_ci_lo: float
    wr_ci_hi: float
    n_decks: int
    # weekly share over the sparkline window, zero-filled, oldest first
    sparkline: list[float]


class MetaResponse(BaseModel):
    game: str
    format: str
    as_of: dt.date
    archetypes: list[MetaArchetype]


class MatchupAxis(BaseModel):
    archetype_id: int
    name: str


class MatchupCell(BaseModel):
    arch_a: int
    arch_b: int
    p_a_beats_b: float
    ci_lo: float
    ci_hi: float
    n_matches: int


class MatchupsResponse(BaseModel):
    game: str
    format: str
    as_of: dt.date
    archetypes: list[MatchupAxis]
    cells: list[MatchupCell]


class MatchupHistoryPoint(BaseModel):
    as_of: dt.date
    p_a_beats_b: float
    ci_lo: float
    ci_hi: float
    n_matches: int


class MatchupDetailResponse(BaseModel):
    game: str
    format: str
    as_of: dt.date
    arch_a: MatchupAxis
    arch_b: MatchupAxis
    p_a_beats_b: float
    ci_lo: float
    ci_hi: float
    n_matches: int
    # change in p vs the previous snapshot; null until two snapshots exist
    trend: float | None
    # premium: the cell across all stored snapshots, oldest first
    history: list[MatchupHistoryPoint] | None
    history_locked: bool


class BestDeck(BaseModel):
    rank: int
    archetype_id: int
    name: str
    exp_winrate_vs_field: float


class BestDecksResponse(BaseModel):
    game: str
    format: str
    as_of: dt.date
    decks: list[BestDeck]


class SeriesPoint(BaseModel):
    week: dt.date
    share: float
    n_decks: int
    # null on zero-deck weeks (no stored posterior for that week)
    winrate: float | None
    wr_ci_lo: float | None
    wr_ci_hi: float | None


class ArchetypeDetailResponse(BaseModel):
    game: str
    format: str
    as_of: dt.date
    archetype_id: int
    name: str
    share: float
    winrate: float
    wr_ci_lo: float
    wr_ci_hi: float
    n_decks: int
    # premium: weekly history, zero-filled over the window, oldest first
    series: list[SeriesPoint] | None
    series_locked: bool


class Mover(BaseModel):
    archetype_id: int
    name: str
    share: float
    prev_share: float
    delta: float
    n_decks: int


class TrendsResponse(BaseModel):
    game: str
    format: str
    week: dt.date
    prev_week: dt.date
    # every archetype present in either week, biggest risers first.
    # Descriptive movement between the last two data weeks — not a forecast
    # (the M3 verdict: share prediction does not ship).
    movers: list[Mover]


class ClassifyCard(BaseModel):
    name: str = Field(min_length=1)
    count: int = Field(ge=1, le=250)
    board: str = Field(min_length=1)


class ClassifyRequest(BaseModel):
    cards: list[ClassifyCard] = Field(min_length=1, max_length=500)


class SpreadCell(BaseModel):
    archetype_id: int
    name: str
    p_win: float
    ci_lo: float
    ci_hi: float
    n_matches: int


class ClassifyResponse(BaseModel):
    game: str
    format: str
    archetype_id: int | None  # null when the archetype has no stored decks yet
    name: str
    method: str
    confidence: float | None
    # names that did not resolve to known cards — reported, never guessed
    unresolved_cards: list[str]
    # matchup spread vs the current snapshot's universe (empty if the
    # archetype is not in it); as_of is the backing snapshot
    as_of: dt.date | None
    matchup_spread: list[SpreadCell]
    exp_winrate_vs_field: float | None


class EventEntry(BaseModel):
    event_id: int
    date: dt.date
    name: str | None
    source: str
    player_count: int | None
    top_archetype_id: int | None
    top_archetype: str | None


class EventsResponse(BaseModel):
    game: str
    format: str
    events: list[EventEntry]
