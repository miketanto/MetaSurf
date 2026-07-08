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
