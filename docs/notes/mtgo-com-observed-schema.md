# mtgo.com/decklists — observed schema (M4 inspection note)

Everything below was observed by fetching **real current pages** from
`https://www.mtgo.com` on **2026-07-07** (with a politely-identified UA) and
inspecting the bytes — headless Chromium for the rendered DOM/network, `curl`
for raw HTML. Nothing here is assumed from documentation, memory, or the old
Badaro cache. The raw pages are saved unmodified under
`tests/fixtures/mtgo.com/`; the parser is written against those fixtures.

This site changed since the Badaro `MTGODecklistCache` scraper broke (June
2025). Do **not** assume the cache's `CacheItem` shape describes the live
site — it describes the *cache*, which is our normalization target, not the
source. The mapping live-page → `CacheItem` is what the M4 parser does.

## ToS / robots (checked 2026-07-07, before any scraping)
- `robots.txt` — **404** on both `mtgo.com` and `www.mtgo.com`; no crawl
  directives exist.
- Decklist pages are public (no auth wall). Footer: "©2026 Daybreak Game
  Company LLC".
- Daybreak ToS §7.1 lists "mine, scrape or expropriate" inside a
  *malware / surreptitious-interference* clause; §13 forbids circumventing
  access-restriction measures (none exist on these public pages). The
  Feb-2026 attempt to restrict decklist publication was **reversed 2026-02-20**
  (`mtgo.com/news/reversing-decklist-changes-02202026`). Owner decision on
  record (this session): proceed with a polite public fetch. See plan §10
  risk 1.

## Listing page: `https://www.mtgo.com/decklists`
- Returns HTTP 200, `text/html`, ~106 KB. Optional month view:
  `?year=YYYY&month=M` (the page exposes Year/Month pickers).
- Individual events are plain anchors: `href="/decklist/<site_name>"`.
  Observed 103 distinct event links on the 2026-07-07 page across Standard,
  Modern, Pioneer, Vintage, Legacy, Pauper, Premodern, Limited, Duel Commander.
- `<site_name>` = `<format>-<event-type>-<YYYY>-<MM>-<DD><id-digits>`, e.g.
  `modern-challenge-64-2026-07-0212846455`, `modern-league-2026-07-0610847`.
  This is the **same slug grammar the Badaro cache used as the filename stem**,
  so the existing `detect_format` (token match) and `derive_event_type`
  (`mtgo.com` slug regex) work on it unchanged. Fixture:
  `listing-decklists-2026-07-07.html`.

## Event page: `https://www.mtgo.com/decklist/<site_name>`
The page embeds a single JSON object as a one-line JS assignment:

```
window.MTGO.decklists.data = { … };      // the event payload (parsed by M4)
window.MTGO.decklists.type = 'tournament';
window.MTGO.decklists.roundNames = [ … ];
```

Card lists are **in this blob**, not lazy-loaded and not in the rendered DOM
(the DOM ships empty `.decklistDecks` / `.decklistStandings` containers plus
Underscore templates that the site's own JS fills from `data` client-side —
we parse `data` directly and never execute their JS). The blob is a single
line; extract it as the text between `window.MTGO.decklists.data =` and the
line-terminating `;`, then `json.loads`.

### Two payload shapes

**Tournament** (`type: TOURNAMENT` — Challenge / Showcase / Qualifier).
Fixture `modern-challenge-32-2026-07-0412846483.html` (32 decklists):
```jsonc
{ "event_id":"12846483", "description":"Modern Challenge 32",
  "starttime":"2026-07-04 06:00:00.0", "format":"CMODERN", "type":"TOURNAMENT",
  "inplayoffs":"1", "url":"…", "site_name":"modern-challenge-32-2026-07-0412846483",
  "decklists":[ {                       // one per published deck
     "loginid":"280670", "tournamentid":"12846483", "decktournamentid":"58589653",
     "player":"FakeShaver",
     "main_deck":[ {"qty":"4","sideboard":"false",
        "card_attributes":{"card_name":"Disrupting Shoal", …}}, … ],
     "sideboard_deck":[ {"qty":"2","sideboard":"true",
        "card_attributes":{"card_name":"Engineered Explosives", …}}, … ] } ],
  "brackets":[ {"index":2,"matches":[ {"players":[
        {"loginid":1636994,"player":"gazmon48","seeding":4,"wins":2,"losses":0,"winner":true},
        {"loginid":2569009,"player":"TrueHero","seeding":5,"wins":0,"losses":2,"winner":false} ]}, … ]} ],
  "standings":[ {"rank":"1","login_name":"FakeShaver","score":"18",
        "opponentmatchwinpercentage":"0.57222","gamewinpercentage":"0.85714",
        "opponentgamewinpercentage":"0.50919","eliminated":"false"}, … ] }
```

**League** (5-0 lists; winner-censored — card-choice signal only, NEVER
winrates). Fixture `modern-league-2026-07-0610847.html` (58 decklists):
```jsonc
{ "playeventid":"10847", "name":"Modern League", "publish_date":"2026-07-06",
  "instance_id":"10847_2026-07-06", "site_name":"modern-league-2026-07-0610847",
  "decklists":[ { "loginid":"…","player":"Valident",
     "main_deck":[…], "sideboard_deck":[…],
     "wins":{"wins":"5","losses":"0"} } ] }   // no brackets, no standings
```

### Field-level facts (verified on the fixtures)
- **Card line** (both `main_deck` and `sideboard_deck`): the useful fields are
  `qty` (string int) and `card_attributes.card_name` (string, unicode e.g.
  `Lórien Revealed`). The redundant per-card `sideboard` flag agrees with
  which array the card is in; we trust the array, not the flag. Everything
  else (`docid`, `ptc`, `cost`, `rarity`, `colors`, …) is ignored — card
  identity resolves through the `cards` table by name (CLAUDE.md rule 3), and
  `card_name` is the canonical Scryfall-style name (` // ` splits, front-face
  DFC names) the existing `CardResolver` already handles.
- **Date**: tournaments carry `starttime` (`"YYYY-MM-DD HH:MM:SS.s"`); leagues
  carry `publish_date` (`"YYYY-MM-DD"`). Either maps to `Tournament.Date`.
- **`format`** field is a MTGO code (`CMODERN`), NOT relied on for format —
  format comes from the `site_name` slug via the existing config-token match,
  exactly like the cache. (Keeps ingest game/format handling config-driven.)
- **Brackets → Rounds.** `brackets` is the Top-8 single-elimination tree;
  index `2/1/0` ⇒ 4/2/1 matches ⇒ `Quarterfinals`/`Semifinals`/`Finals` (same
  round vocabulary the cache used for mtgo challenges, confirming the M2 match
  extractor consumes them unchanged). Each match's `players[0]` vs
  `players[1]` with `wins`/`losses` maps to `{Player1, Player2, Result:
  "wins-losses-0"}` from Player1's perspective — the orientation the extractor
  documents and requires. Byes / missing players not observed in brackets.
- **Standings** carry `rank`, `score` (match points), and OMWP/GWP/OGWP, but
  **no per-player Wins/Losses/Draws** (a difference from the older cache
  standings, which had them). The normalizer tolerates missing Wins/Losses; a
  challenge deck's `finish_rank` comes from the standings `rank`, and true
  match evidence comes from `brackets`→`Rounds` (the intended winrate path).
- **Not every event has decklists.** `modern-challenge-64-2026-07-0212846455`
  (fixture `…-no-decklists.html`) returned a 13.8 KB blob with `standings`,
  `brackets`, `winloss`, `final_rank`, `player_count` but **no `decklists`
  key** — decklists were not (yet) published for it. The parser treats a
  missing/empty `decklists` as "no decks to import" (0 decks), never an error.
- **Missing events 302-redirect** to `/decklists` (observed on league slugs
  whose day isn't published yet). The fetcher treats a cross-host/again-to-
  listing 302 as "not available yet", not a hard failure.
- **Key sets vary between events** (the no-decklists challenge exposed
  `winloss`/`final_rank`/`player_count`; the with-decklists one did not). The
  parser reads only the keys it needs and `.get()`s everything.

## M4 normalization decisions driven by the above
- The scraper emits a `CacheItem`-shaped JSON file per event
  (`Tournament`/`Decks`/`Rounds`/`Standings`) into a
  `Tournaments/mtgo.com/<YYYY>/<MM>/<DD>/<site_name>.json` layout, so the
  existing `ingest.normalize.cache_item.normalize_file`,
  `ingest.cache_import.importer`, and `ingest.match_extract` consume it with
  **zero changes**. `site_name` is the filename stem and the
  `(source='mtgo.com', source_event_id=site_name)` dedupe key.
- The **raw HTML** response is archived immutably first
  (`data/raw/mtgo.com/<YYYY>/<MM>/<DD>/<site_name>.html`) before any parsing;
  the `CacheItem` JSON is regenerable from it, so improving the parser and
  reprocessing history is always possible (plan §1 "raw data is sacred").
- League `Decks` get `Result` = `"<wins>-<losses>"` (e.g. `"5-0"`); no
  `Standings`, no `Rounds`. Tournament `Decks` get `Result` = the standings
  rank rendered as `"<rank>(st|nd|rd|th) Place"` and full `Standings` +
  `Rounds` (from brackets). Both are shapes `parse_result` already handles.
- Cards resolve through `CardResolver`/`cards`; unresolved names log to
  `ingest_unresolved_cards`, never guessed (unchanged).
