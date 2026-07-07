"""Normalizer tests against real saved fixtures (no mocks of the unit under test).

Expected values below were read from the fixture files themselves during the
M0 inspection (docs/notes/mtgodecklistcache-observed-schema.md).
"""

from __future__ import annotations

from datetime import date

from ingest.formats_config import load_formats
from ingest.normalize.cache_item import detect_format, normalize_file, parse_result
from tests.conftest import FIXTURES

TOKENS = {f.name: f.slug_tokens for f in load_formats()}


def _norm(rel: str):
    path = FIXTURES / "Tournaments" / rel
    source = rel.split("/")[0]
    return normalize_file(path, FIXTURES, source)


class TestParseResult:
    def test_league_record(self):
        assert parse_result("5-0") == (None, 5, 0, None)

    def test_swiss_record(self):
        assert parse_result("4-0") == (None, 4, 0, None)

    def test_place(self):
        assert parse_result("1st Place") == (1, None, None, None)
        assert parse_result("2nd Place") == (2, None, None, None)
        assert parse_result("3rd Place") == (3, None, None, None)
        assert parse_result("14th Place") == (14, None, None, None)

    def test_empty_and_none(self):
        # 3,120 Modern decks in the corpus have Result == ""
        assert parse_result("") == (None, None, None, None)
        assert parse_result(None) == (None, None, None, None)

    def test_unknown_pattern_returns_nones(self):
        assert parse_result("Winner") == (None, None, None, None)


class TestDetectFormat:
    def test_mtgo_prefix(self):
        assert detect_format("modern-league-2023-03-037132.json", TOKENS) == "modern"

    def test_melee_embedded_token(self):
        name = "grand-open-qualifier-prague-2024-modern-59235-2024-03-23.json"
        assert detect_format(name, TOKENS) == "modern"

    def test_no_token_returns_none(self):
        # real case: MOCS events carry no format token — must not be guessed
        assert detect_format("2019-mocs-open-2019-03-0911818115.json", TOKENS) is None

    def test_other_format(self):
        assert detect_format("legacy-league-2023-01-057038.json", TOKENS) == "legacy"


class TestMtgo2016DailySwiss:
    REL = "mtgo.com/2016/03/23/modern-daily-swiss-2016-03-239485836.json"

    def test_event_fields(self):
        ev = _norm(self.REL)
        assert ev.source == "mtgo.com"
        assert ev.source_event_id == "modern-daily-swiss-2016-03-239485836"
        assert ev.name == "Modern Daily Swiss"
        assert ev.event_date == date(2016, 3, 23)
        assert ev.event_type == "daily-swiss"
        assert len(ev.decks) == 25
        assert ev.player_count == 24  # standings rows (field size)

    def test_standings_merge(self):
        ev = _norm(self.REL)
        top = next(d for d in ev.decks if d.player == "_goblinlackey")
        assert (top.wins, top.losses, top.draws) == (4, 0, 0)
        assert top.finish_rank == 1


class TestMtgo2020Challenge:
    REL = "mtgo.com/2020/03/21/modern-challenge-2020-03-2112110950.json"

    def test_counts(self):
        ev = _norm(self.REL)
        # observed: 261 published decks but only 252 standings rows
        assert len(ev.decks) == 261
        assert ev.player_count == 252
        assert ev.decks_without_standing > 0
        assert ev.event_type == "challenge"

    def test_winner_rank_from_standings(self):
        ev = _norm(self.REL)
        winner = next(d for d in ev.decks if d.player == "nahuel10")
        assert winner.finish_rank == 1
        assert (winner.wins, winner.losses) == (10, 2)


class TestMtgo2023League:
    REL = "mtgo.com/2023/03/03/modern-league-2023-03-037132.json"

    def test_no_standings_record_from_result(self):
        ev = _norm(self.REL)
        assert ev.event_type == "league"
        assert all(d.wins == 5 and d.losses == 0 for d in ev.decks)
        assert all(d.finish_rank is None for d in ev.decks)
        assert ev.player_count == len(ev.decks) == 69


class TestMtgoLimitedData2024Challenge32:
    REL = "mtgo.com_limited_data/2024/11/23/modern-challenge-32-2024-11-2312706762.json"

    def test_event_type_slug(self):
        ev = _norm(self.REL)
        assert ev.event_type == "challenge-32"
        assert len(ev.decks) == 32
        assert ev.player_count == 32


class TestMeleeZeroCardDeck:
    REL = (
        "melee.gg/2023/03/03/"
        "modern-20k-trial-scg-con-charlotte-friday-100-pm-silver-14033-2023-03-03.json"
    )

    def test_zero_mainboard_deck_is_kept_and_visible(self):
        ev = _norm(self.REL)
        assert ev.event_type == "tournament"
        # real melee artifact (verified in the raw file): NicolasP1 finished
        # 14th with 0 mainboard cards and 2 sideboard cards recorded
        empty_mains = [
            d for d in ev.decks if not any(c.board == "main" for c in d.cards)
        ]
        assert len(empty_mains) >= 1
        assert any(d.player == "NicolasP1" for d in empty_mains)

    def test_null_deck_dates_do_not_break_event_date(self):
        ev = _norm(self.REL)
        assert ev.event_date == date(2023, 3, 3)


class TestTopdeckStandingsOnlyPlayers:
    REL = "topdeck.gg/2024/11/23/the-ocho-modern-RJ0ZRODZmPjRmypf0oHr-2024-11-23.json"

    def test_standings_only_counted_not_fabricated(self):
        ev = _norm(self.REL)
        # observed: 19 decks, 21 standings rows -> 2 standings-only players
        assert len(ev.decks) == 19
        assert ev.standings_only_players == 2
        assert ev.player_count == 21


class TestEmptyResultPreliminary:
    REL = "mtgo.com/2019/12/23/modern-preliminary-2019-12-2312052872.json"

    def test_empty_result_yields_null_record(self):
        ev = _norm(self.REL)
        empty = [d for d in ev.decks if d.result_raw is None]
        assert len(empty) > 0
        assert all(d.wins is None and d.finish_rank is None for d in empty)


class TestCardAggregation:
    def test_counts_summed_and_sorted(self):
        ev = _norm(TestMtgo2016DailySwiss.REL)
        deck = ev.decks[0]
        mains = [c for c in deck.cards if c.board == "main"]
        assert sum(c.count for c in mains) == 60
        assert mains == sorted(mains, key=lambda c: (c.name, c.board))


class TestZeroCountCardLines:
    # melee.gg file observed with literal {"Count": 0, ...} entries: player
    # 'Hudson Tinch' has Count 0 lines for 'Flooded Strand' and
    # 'Snow-Covered Island' (the only such entries in the file)
    REL = "melee.gg/2022/10/08/modern-30k-scg-con-dallas-saturday-1000-am-11807-2022-10-08.json"

    def test_zero_count_entries_dropped_and_counted(self):
        ev = _norm(self.REL)
        assert ev.zero_count_card_lines == 2
        deck = next(d for d in ev.decks if d.player == "Hudson Tinch")
        names = {c.name for c in deck.cards}
        assert "Flooded Strand" not in names
        assert "Snow-Covered Island" not in names
        assert all(c.count >= 1 for d in ev.decks for c in d.cards)
