"""Live scraper for mtgo.com/decklists (plan §3, §6, milestone M4).

We build and own this scraper. It fetches the public decklist pages, archives
the raw HTML immutably, and parses each event into the same CacheItem shape the
frozen MTGODecklistCache used, so the existing normalize / import / match-
extract code paths ingest live events with zero changes.

Politeness (CLAUDE.md, plan §11): custom UA identifying the project,
<=1 req/sec/host, exponential backoff, cache everything, never re-fetch an
archived event. Raw responses hit the archive before any parsing.
"""
