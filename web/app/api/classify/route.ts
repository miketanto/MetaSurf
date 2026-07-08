import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_BASE ?? "http://localhost:8000";

// Server-side proxy to the FastAPI /classify (avoids browser CORS and keeps the
// entitlement server-side). NOTE: /classify is premium-gated; until real auth
// exists we send the premium flag here so the importer works. Swap this for a
// per-user entitlement once accounts land.
export async function POST(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const game = searchParams.get("game") ?? "mtg";
  const format = searchParams.get("format") ?? "modern";
  const body = await req.text();

  const res = await fetch(`${API_BASE}/v1/${game}/${format}/classify`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Entitlements": "premium" },
    body,
    cache: "no-store",
  });

  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
