# Melee.gg API access — request email (draft)

Send to **contact@melee.gg**. Fill the `[bracketed]` placeholders. If you're
requesting data for tournaments/organizations you don't own, the owner of each
must separately email contact@melee.gg to approve (Melee's requirement, since
the data can include player PII).

---

**To:** contact@melee.gg
**Subject:** Tournament Data API access request — [MetaSurf / your product name]

Hello Melee team,

I'm [your name], [your role] at [MetaSurf / your org]. We're building a
Magic: The Gathering **metagame-analytics product** — archetype breakdowns,
matchup winrates, and trend tracking — currently sourced from Magic Online and
first-party partners, and we'd like to include Melee tournament data through
your Tournament Data API.

**What we're requesting**
- API access (client ID / secret) to the Tournament Data API, per
  https://help.melee.gg/docs/api-use/.
- Read access to **completed** Constructed tournament data: decklists,
  standings, and round pairings/results (we do not need registration or any
  live/in-progress data).
- Formats of interest to start: **Modern** (expanding to other Constructed
  formats later).

**Scope / basis for access**
[Choose one and delete the other:]
- We run/co-run events on Melee and are requesting access for our own
  organization: **[org name / event links]**.
- We're seeking a data partnership. We understand access to another
  organization's data requires that organization to approve at
  contact@melee.gg; we're happy to coordinate that with the TOs we work with:
  **[list, if any]**.

**Data handling & attribution**
- We will handle any personally identifiable information (player names, etc.)
  in accordance with your terms — stored only as needed for public tournament
  results, never sold or shared, and removed on request.
- We will display clear **attribution and a link back to Melee.gg** on every
  surface that uses Melee data.
- We archive raw responses immutably and can honor rate limits, deletion
  requests, and any coverage-staff/PII constraints you specify.

Could you let us know the steps to obtain credentials, any terms or rate
limits we should design around, and whether a partnership arrangement is the
right path for broader coverage? Happy to hop on a call.

Thank you,
[your name]
[your role, MetaSurf]
[email / contact]

---

**After you send:** once they issue a client ID + secret, hand them to me via
a private env (not chat) and I'll build the Melee adapter into the same
best-effort seam as MTGO/TopDeck (inspect real API responses → fixtures →
parser → CacheItem → existing normalize/import). Melee's full swiss pairings
are the richest matchup-winrate signal we can get for paper events.
