"""/v1/{game}/{format}/... read endpoints (M5, plan §7 + §8 screens).

Free vs premium per the handoff's endpoint table; every premium gate goes
through the entitlements module. All data comes from rollup tables written
by jobs/rollups — nothing is computed per request beyond name joins and
zero-filling weekly series.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api import queries
from api.attribution import credits_for
from api.classifier import CardLine, ClassifierService
from api.db import Conn
from api.entitlements import PREMIUM, Entitled
from api.schemas import (
    ArchetypeDetailResponse,
    BestDeck,
    BestDecksResponse,
    ClassifyRequest,
    ClassifyResponse,
    EventEntry,
    EventsResponse,
    MatchupAxis,
    MatchupCell,
    MatchupDetailResponse,
    MatchupHistoryPoint,
    MatchupsResponse,
    MetaArchetype,
    MetaResponse,
    Mover,
    SeriesPoint,
    SpreadCell,
    TrendsResponse,
)

SPARKLINE_WEEKS = 8
DEFAULT_SERIES_WEEKS = 13  # ~90 days
WEEK = dt.timedelta(days=7)

router = APIRouter(prefix="/v1/{game}/{format}")


@dataclass(frozen=True)
class FormatCtx:
    format_id: int
    game: str
    format_name: str


def resolve_format(game: str, format: str, conn: Conn) -> FormatCtx:
    format_id = queries.resolve_format_id(conn, game, format)
    if format_id is None:
        raise HTTPException(status_code=404, detail="unknown game/format")
    return FormatCtx(format_id=format_id, game=game, format_name=format)


Ctx = Annotated[FormatCtx, Depends(resolve_format)]
AsOf = Annotated[dt.date | None, Query(description="snapshot date; default: latest")]


def _snapshot(conn: Conn, table: str, ctx: FormatCtx, as_of: dt.date | None) -> dt.date:
    resolved = as_of or queries.latest_snapshot(conn, table, ctx.format_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="no rollup snapshot for this format")
    return resolved


@router.get("/meta", response_model=MetaResponse)
def meta(ctx: Ctx, conn: Conn, as_of: AsOf = None) -> MetaResponse:
    """S1 meta snapshot (free): archetypes by share with winrate CI and a
    weekly share sparkline."""
    snap = _snapshot(conn, "rollup_meta", ctx, as_of)
    rows = queries.meta_rows(conn, ctx.format_id, snap)
    if not rows:
        raise HTTPException(status_code=404, detail="no rollup snapshot for this date")
    names = queries.archetype_names(conn, ctx.format_id)
    first = snap - SPARKLINE_WEEKS * WEEK
    grid = queries.week_grid(conn, ctx.format_id, first, snap)
    shares = queries.weekly_shares(conn, ctx.format_id, first, snap)
    return MetaResponse(
        game=ctx.game,
        format=ctx.format_name,
        as_of=snap,
        archetypes=[
            MetaArchetype(
                archetype_id=arch,
                name=names[arch],
                share=share,
                winrate=wr,
                wr_ci_lo=lo,
                wr_ci_hi=hi,
                n_decks=n,
                sparkline=[shares.get(arch, {}).get(week, 0.0) for week in grid],
            )
            for arch, share, wr, lo, hi, n in rows
        ],
    )


@router.get("/matchups", response_model=MatchupsResponse)
def matchups(ctx: Ctx, conn: Conn, as_of: AsOf = None) -> MatchupsResponse:
    """S2 matchup matrix (free): every cell over the snapshot's universe."""
    snap = _snapshot(conn, "rollup_matchups", ctx, as_of)
    rows = queries.matchup_rows(conn, ctx.format_id, snap)
    if not rows:
        raise HTTPException(status_code=404, detail="no rollup snapshot for this date")
    names = queries.archetype_names(conn, ctx.format_id)
    axis = sorted({r[0] for r in rows})
    return MatchupsResponse(
        game=ctx.game,
        format=ctx.format_name,
        as_of=snap,
        archetypes=[MatchupAxis(archetype_id=a, name=names[a]) for a in axis],
        cells=[
            MatchupCell(
                arch_a=a, arch_b=b, p_a_beats_b=p, ci_lo=lo, ci_hi=hi, n_matches=n
            )
            for a, b, p, lo, hi, n in rows
        ],
    )


@router.get("/matchups/{arch_a}/{arch_b}", response_model=MatchupDetailResponse)
def matchup_detail(
    ctx: Ctx, conn: Conn, arch_a: int, arch_b: int, ent: Entitled, as_of: AsOf = None
) -> MatchupDetailResponse:
    """S2 cell detail: winrate, CI, sample size, trend (free); the cell's
    history across snapshots (premium)."""
    snap = _snapshot(conn, "rollup_matchups", ctx, as_of)
    history = queries.matchup_cell_history(conn, ctx.format_id, arch_a, arch_b, snap)
    current = [h for h in history if h[0] == snap]
    if not current:
        raise HTTPException(status_code=404, detail="no matchup data for this pair")
    _, p, lo, hi, n = current[0]
    prev = [h for h in history if h[0] < snap]
    names = queries.archetype_names(conn, ctx.format_id)
    return MatchupDetailResponse(
        game=ctx.game,
        format=ctx.format_name,
        as_of=snap,
        arch_a=MatchupAxis(archetype_id=arch_a, name=names[arch_a]),
        arch_b=MatchupAxis(archetype_id=arch_b, name=names[arch_b]),
        p_a_beats_b=p,
        ci_lo=lo,
        ci_hi=hi,
        n_matches=n,
        trend=(p - prev[-1][1]) if prev else None,
        history=[
            MatchupHistoryPoint(
                as_of=h_as_of, p_a_beats_b=h_p, ci_lo=h_lo, ci_hi=h_hi, n_matches=h_n
            )
            for h_as_of, h_p, h_lo, h_hi, h_n in history
        ]
        if ent.has(PREMIUM)
        else None,
        history_locked=not ent.has(PREMIUM),
    )


@router.get("/best-decks", response_model=BestDecksResponse)
def best_decks(ctx: Ctx, conn: Conn, as_of: AsOf = None) -> BestDecksResponse:
    """S2/S6 ranked best-positioned archetypes vs the current field (free)."""
    snap = _snapshot(conn, "rollup_best_decks", ctx, as_of)
    rows = queries.best_deck_rows(conn, ctx.format_id, snap)
    if not rows:
        raise HTTPException(status_code=404, detail="no rollup snapshot for this date")
    names = queries.archetype_names(conn, ctx.format_id)
    return BestDecksResponse(
        game=ctx.game,
        format=ctx.format_name,
        as_of=snap,
        decks=[
            BestDeck(rank=rank, archetype_id=arch, name=names[arch], exp_winrate_vs_field=s)
            for rank, arch, s in rows
        ],
    )


@router.get("/archetypes/{archetype_id}", response_model=ArchetypeDetailResponse)
def archetype_detail(
    ctx: Ctx,
    conn: Conn,
    archetype_id: int,
    ent: Entitled,
    as_of: AsOf = None,
    weeks: Annotated[int, Query(ge=1, le=52, description="series window")] = (
        DEFAULT_SERIES_WEEKS
    ),
) -> ArchetypeDetailResponse:
    """S3 archetype detail: current share/winrate (free); weekly share +
    winrate series over the requested window (premium)."""
    snap = _snapshot(conn, "rollup_meta", ctx, as_of)
    row = [r for r in queries.meta_rows(conn, ctx.format_id, snap) if r[0] == archetype_id]
    if not row:
        raise HTTPException(status_code=404, detail="archetype not in the current snapshot")
    _, share, wr, lo, hi, n = row[0]
    names = queries.archetype_names(conn, ctx.format_id)

    series: list[SeriesPoint] | None = None
    if ent.has(PREMIUM):
        first = snap - weeks * WEEK
        grid = queries.week_grid(conn, ctx.format_id, first, snap)
        points = queries.series_rows(conn, ctx.format_id, archetype_id, first, snap)
        series = []
        for week in grid:
            if week in points:
                w_share, w_wr, w_lo, w_hi, w_n = points[week]
                series.append(
                    SeriesPoint(
                        week=week,
                        share=w_share,
                        n_decks=w_n,
                        winrate=w_wr,
                        wr_ci_lo=w_lo,
                        wr_ci_hi=w_hi,
                    )
                )
            else:  # data week where this archetype put up no decks
                series.append(
                    SeriesPoint(
                        week=week, share=0.0, n_decks=0, winrate=None, wr_ci_lo=None, wr_ci_hi=None
                    )
                )
    return ArchetypeDetailResponse(
        game=ctx.game,
        format=ctx.format_name,
        as_of=snap,
        archetype_id=archetype_id,
        name=names[archetype_id],
        share=share,
        winrate=wr,
        wr_ci_lo=lo,
        wr_ci_hi=hi,
        n_decks=n,
        series=series,
        series_locked=not ent.has(PREMIUM),
    )


@router.get("/trends", response_model=TrendsResponse)
def trends(ctx: Ctx, conn: Conn, ent: Entitled) -> TrendsResponse:
    """S5 movers (premium): share change between the last two data weeks.
    Descriptive only — the M3 verdict rules out share forecasts. The
    contrarian 'overextended' flag (BL-4) ships after its forward test."""
    if not ent.has(PREMIUM):
        raise HTTPException(status_code=403, detail="premium entitlement required")
    weeks = queries.last_data_weeks(conn, ctx.format_id, 2)
    if len(weeks) < 2:
        raise HTTPException(status_code=404, detail="not enough weekly data for trends")
    prev_week, week = weeks
    prev = queries.week_shares(conn, ctx.format_id, prev_week)
    cur = queries.week_shares(conn, ctx.format_id, week)
    names = queries.archetype_names(conn, ctx.format_id)
    movers = [
        Mover(
            archetype_id=arch,
            name=names[arch],
            share=cur.get(arch, (0.0, 0))[0],
            prev_share=prev.get(arch, (0.0, 0))[0],
            delta=cur.get(arch, (0.0, 0))[0] - prev.get(arch, (0.0, 0))[0],
            n_decks=cur.get(arch, (0.0, 0))[1],
        )
        for arch in sorted(set(prev) | set(cur))
    ]
    movers.sort(key=lambda m: (-m.delta, m.archetype_id))
    return TrendsResponse(
        game=ctx.game, format=ctx.format_name, week=week, prev_week=prev_week, movers=movers
    )


def get_classifier(ctx: Ctx, request: Request) -> ClassifierService:
    """The game's injected ClassifierService (see api/classifier.py)."""
    service: ClassifierService | None = request.app.state.classifiers.get(ctx.game)
    if service is None:
        raise HTTPException(
            status_code=501, detail="classification not available for this game"
        )
    return service


@router.post("/classify", response_model=ClassifyResponse)
def classify_deck(
    ctx: Ctx,
    conn: Conn,
    ent: Entitled,
    body: ClassifyRequest,
    service: Annotated[ClassifierService, Depends(get_classifier)],
) -> ClassifyResponse:
    """S6 (premium, live): classify a pasted list, then answer from rollups —
    the archetype's matchup spread vs the current universe and its
    best-positioned score. Unresolvable card names are reported, never
    guessed."""
    if not ent.has(PREMIUM):
        raise HTTPException(status_code=403, detail="premium entitlement required")
    try:
        result = service.classify_deck(
            conn,
            ctx.format_name,
            [CardLine(name=c.name, count=c.count, board=c.board) for c in body.cards],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    archetype_id = queries.archetype_id_by_name(conn, ctx.format_id, result.archetype_name)
    snap = queries.latest_snapshot(conn, "rollup_matchups", ctx.format_id)
    spread: list[SpreadCell] = []
    score: float | None = None
    if archetype_id is not None and snap is not None:
        names = queries.archetype_names(conn, ctx.format_id)
        spread = [
            SpreadCell(
                archetype_id=b, name=names[b], p_win=p, ci_lo=lo, ci_hi=hi, n_matches=n
            )
            for b, p, lo, hi, n in queries.matchup_spread_row(
                conn, ctx.format_id, snap, archetype_id
            )
        ]
        score = queries.best_deck_score(conn, ctx.format_id, snap, archetype_id)
    return ClassifyResponse(
        game=ctx.game,
        format=ctx.format_name,
        archetype_id=archetype_id,
        name=result.archetype_name,
        method=result.method,
        confidence=result.confidence,
        unresolved_cards=list(result.unresolved_cards),
        as_of=snap,
        matchup_spread=spread,
        exp_winrate_vs_field=score,
    )


@router.get("/events", response_model=EventsResponse)
def events(
    ctx: Ctx,
    conn: Conn,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> EventsResponse:
    """S4 recent-results feed (free), newest first."""
    rows = queries.event_rows(conn, ctx.format_id, limit)
    names = queries.archetype_names(conn, ctx.format_id)
    return EventsResponse(
        game=ctx.game,
        format=ctx.format_name,
        events=[
            EventEntry(
                event_id=event_id,
                date=date,
                name=name,
                source=source,
                player_count=players,
                top_archetype_id=top,
                top_archetype=names.get(top) if top is not None else None,
            )
            for event_id, date, name, source, players, top in rows
        ],
        credits=credits_for({source for _, _, _, source, _, _ in rows}),
    )
