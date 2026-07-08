// Mirrors the FastAPI response models (api/schemas.py). Kept in sync by hand
// for now; a generated client from the committed OpenAPI is a later step.

export interface MetaArchetype {
  archetype_id: number;
  name: string;
  share: number; // 0..1 fraction of the field
  winrate: number; // 0..1
  wr_ci_lo: number;
  wr_ci_hi: number;
  n_decks: number;
  sparkline: number[]; // weekly share, oldest first, zero-filled
}

export interface MetaResponse {
  game: string;
  format: string;
  as_of: string; // ISO date
  archetypes: MetaArchetype[];
}

export interface MatchupAxis {
  archetype_id: number;
  name: string;
}

export interface MatchupCell {
  arch_a: number;
  arch_b: number;
  p_a_beats_b: number; // 0..1 probability A beats B
  ci_lo: number;
  ci_hi: number;
  n_matches: number;
}

export interface MatchupsResponse {
  game: string;
  format: string;
  as_of: string;
  archetypes: MatchupAxis[];
  cells: MatchupCell[];
}

export interface SpreadCell {
  archetype_id: number;
  name: string;
  p_win: number;
  ci_lo: number;
  ci_hi: number;
  n_matches: number;
}

export interface ClassifyResponse {
  game: string;
  format: string;
  archetype_id: number | null;
  name: string;
  method: string; // "rules" | "fallback"
  confidence: number | null;
  unresolved_cards: string[];
  as_of: string | null;
  matchup_spread: SpreadCell[];
  exp_winrate_vs_field: number | null;
}
