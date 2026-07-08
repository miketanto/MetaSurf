import type { MetaResponse } from "./types";

const API_BASE = process.env.API_BASE ?? "http://localhost:8000";

// The premium tier is requested with an `X-Entitlements: premium` header
// (api/entitlements.py). The free web tier simply omits it — free responses
// carry the premium sections as locked placeholders.
export type Tier = "free" | "premium";

function headers(tier: Tier): HeadersInit {
  return tier === "premium" ? { "X-Entitlements": "premium" } : {};
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public url: string,
  ) {
    super(`API ${status} for ${url}`);
  }
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
  return getJson<MetaResponse>(`/v1/${game}/${format}/meta`, tier);
}

// Formats the read API can currently serve (import-enabled). A /formats
// discovery endpoint would replace this hard-coded list later.
export const KNOWN_FORMATS: { game: string; format: string; label: string }[] = [
  { game: "mtg", format: "modern", label: "Modern" },
  { game: "mtg", format: "standard", label: "Standard" },
];
