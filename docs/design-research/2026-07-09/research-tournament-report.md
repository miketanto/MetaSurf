# Research: Tournament Report / Match Logging UX (2026-07-10)

Findings from live web research (all sources fetched or search-verified in-session; caveats at end). Each finding: pattern → pit-wall translation.

## 1. Automatic capture beats manual entry — but only where a client exists
Untapped.gg Companion records Arena matches automatically (result, opponent, deck) via client integration; opponent deck is identified progressively from cards played, not declared. 17Lands uses Arena's opt-in detailed logs. MTGO tools (MyMTGO, MTGO-Tracker) parse local `Match_GameLog_*.dat`. Paper has no log file — every paper tool falls back to a manual form. Lesson: the manual path competes with "zero keystrokes," so minimize it.
*Sources: mtga.untapped.gg/companion (fetched), blog.17lands.com, mymtgo.com (snippets; 403 direct), cderickson.io/mtgo-tracker (fetched)*
**Translation:** paper log = "manual timing sheet," completable one-thumbed between rounds in <15s: big DSEG score steppers, archetype typeahead, everything else optional. Future MTGO/Arena imports appear on the same stint log tagged AUTO vs MANUAL (source LED per row).

## 2. The round is the atomic unit with a fixed natural schema
Melee.gg round = round number, table, opponent, result (winner submits, loser confirms). MTG Match Tracker converges: game W/L, turn order, opponents, decks/versions, notes. Canonical record: (round_no, opponent_name?, opponent_archetype?, game score W-L-D, play/draw?, notes?). Everything after opponent_name optional.
*Sources: help.melee.gg (search-verified), bazaarofboxes.com/mtgmeleeguide (fetched), MTG Match Tracker App Store page (fetched)*
**Translation:** report form = stack of "lap cards" (R1, R2, R3…): round number in a riso corner tab, archetype select center, game score as three-segment DSEG (2-1-0) tap-to-increment. Running record totals live at top like a timing tower.

## 3. Honest NA defaults — never force a guess
MTGO-Tracker: fields that can't be read from logs "import as NA by default and are input manually." Unknown is a first-class stored value, not a validation error; enrichment is deferred and optional.
*Source: cderickson.io/mtgo-tracker (fetched)*
**Translation:** "UNKNOWN" tops the archetype select as a dim dashed slot (`— NO ID —`), never an error. Unknowns aggregate into an explicit "unidentified" bucket; a subtle "3 rounds missing opponent ID" chip invites backfill without blocking save.

## 4. Winner-submits, opponent-confirms (two-party integrity, one-party effort)
Melee and Wizards Companion both: one player submits, the other confirms/ratifies.
*Sources: help.melee.gg, magic-support.wizards.com Companion FAQ (search-verified)*
**Translation:** V1 personal logs carry a "SELF-REPORTED" scrutineering stamp. Reserve `confirmed_by` in the schema now so a future both-players-logged handshake upgrades entries to VERIFIED without migration.

## 5. Event container first, rounds second — self-created events are a supported peer
Wizards Companion supports self-tracking or store pairing; ending the event finalizes it; profile shows event name/date/store/results. TCG Match Tracker: events carry format/standing/record, matches attach. Flow: create-or-join event container → log rounds → close.
*Sources: magic.wizards.com Companion pages (search-verified), tcgmatchtracker.app/magic (fetched)*
**Translation:** "race entry" screen: typeahead over MetaSurf's real ingested events (by date/format) OR one tap "LOCAL EVENT" minting a private one (name/store/format/date). Chips: "PRIVATE CIRCUIT" (riso gradient) vs "SANCTIONED GRID" — provenance always visible. Explicit "END STINT" freezes the record.

## 6. Crowd submission proves minimal requirements (mtgtop8)
Required: precise event title (dedup), format, date, player count; per deck player+rank; archetype optional (auto-assigned). Forgiving list parsing (case-insensitive, `SB:` prefix). Two decades of submissions on this schema.
*Sources: mtgtop8.com/submit_event_howto (fetched), /submit (search-verified)*
**Translation:** user supplies only facts they alone know (event, rounds, scores); platform supplies classification (M1 rule-file classifier on their pasted list). Typeahead-match-first, free-text-create fallback.

## 7. Deck-version granularity and play/draw are power-user fields
Match Tracker logs deck versions + turn order → turn-order stats; Untapped tracks how deck changes affect winrate; MTGO-Tracker captures play/draw. Always optional.
**Translation:** each lap card gets a collapsed "setup sheet" drawer: P/D indicator lamp toggle, deck-version tag (chassis spec → saved list snapshot), notes. The 15-second happy path never sees it. Play-vs-draw = paired gauge in personal stats.

## 8. Aggregation payoff = winrate-vs-archetype with sample sizes shown
MyMTGO/Deck Tracker/Match Tracker/Untapped all converge: per-archetype personal winrates with n displayed; small-n honesty is the norm.
**Translation:** personal stats = "matchup telemetry board": row per opponent archetype, DSEG winrate, small n beside it, confidence dimmer — n<5 rows at reduced opacity with LOW SAMPLE flag. Riso-accent trend sparkline per row.

## 9. "Local meta vs global meta" is a real gap, not a solved feature
Direct search found only global trackers; nobody renders "what I face at my store vs the format globally."
**Translation:** MetaSurf differentiator, cheap once logs exist: dual-bar "track conditions" panel per archetype — global share vs share-of-your-rounds, delta highlighted ("you face Burn 2.3× more than the field").

## 10. Immutability with an escape hatch; edits are privileged
Melee: players can't edit submitted results (TO only). Companion auto-finalizes unclosed events after a week. Append-mostly with deliberate correction paths.
**Translation:** personal logs editable but carry an edited-at marker (wrench glyph); aggregates recompute visibly. Auto-close stale open events after N days into a "provisional" state.

## 11. Narrative belongs beside the numbers
Every logger studied includes per-match free-text notes; the community tournament-report genre (deck choice → round-by-round narrative) is the ancestral format (genre structure: convention, not verified this session — reddit unreachable).
**Translation:** per-round notes = "radio messages" (mono one-liners under the lap card). A completed event auto-composes a shareable stint report: header (deck, event, final DSEG record) + lap cards + radio messages — the classic tournament report generated from structured data.

## 12. Export is trust collateral
TCG Match Tracker and MTGO-Tracker both ship CSV/XLSX export of the user's own data; portability is a selling point for grinders.
**Translation:** "DOWNLOAD TELEMETRY" action (CSV of rounds). Gate analysis, never the user's own raw laps — consistent with the entitlements posture.

## Caveats
mymtgo.com claims from search snippets only (403 direct). Melee submit/confirm verified via search + the fetched Bazaar of Boxes guide. Reddit unreachable → finding 11's genre template flagged as convention. mtgeloproject.net is a curated historical archive (~1,785 events), NOT a personal logger — precedent for event-database ingestion only.
