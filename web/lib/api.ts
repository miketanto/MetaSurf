import type { MetaResponse, MatchupsResponse } from "./types";

const API_BASE = process.env.API_BASE ?? "http://localhost:8000";

// The premium tier is requested with an `X-Entitlements: premium` header
// (api/entitlements.py). The free web tier simply omits it — free responses
// carry the premium sections as locked placeholders.
export type Tier = "free" | "premium";

function headers(tier: Tier): HeadersInit {
  return tier === "premium" ? { "X-Entitlements": "premium" } : {};
}

// TEMPORARY: live ingestion only started recently, so the latest rollup
// snapshot is thin. Until daily data accrues, pin the read views to the most
// recent data-rich snapshot per format. Remove this map to fall back to latest.
const SNAPSHOT: Record<string, string | undefined> = {
  "mtg/modern": "2025-03-15",
};

export function snapshotFor(game: string, format: string): string | undefined {
  return SNAPSHOT[`${game}/${format}`];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public url: string,
  ) {
    super(`API ${status} for ${url}`);
  }
}

function withAsOf(path: string, asOf?: string): string {
  return asOf ? `${path}${path.includes("?") ? "&" : "?"}as_of=${asOf}` : path;
}

async function getJson<T>(path: string, tier: Tier = "free"): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, { headers: headers(tier), cache: "no-store" });
  if (!res.ok) throw new ApiError(res.status, url);
  return (await res.json()) as T;
}

export function getMeta(
  game: string,
  format: string,
  tier: Tier = "free",
): Promise<MetaResponse> {
  const path = withAsOf(`/v1/${game}/${format}/meta`, snapshotFor(game, format));
  return getJson<MetaResponse>(path, tier);
}

export function getMatchups(
  game: string,
  format: string,
  tier: Tier = "free",
): Promise<MatchupsResponse> {
  const path = withAsOf(`/v1/${game}/${format}/matchups`, snapshotFor(game, format));
  return getJson<MatchupsResponse>(path, tier);
}

// Formats the read API can currently serve (import-enabled). A /formats
// discovery endpoint would replace this hard-coded list later.
export const KNOWN_FORMATS: { game: string; format: string; label: string }[] = [
  { game: "mtg", format: "modern", label: "Modern" },
  { game: "mtg", format: "standard", label: "Standard" },
];
