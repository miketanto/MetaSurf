import { MetaTable } from "@/components/MetaTable";
import { LockedPanel } from "@/components/LockedPanel";
import { getMeta, KNOWN_FORMATS, ApiError } from "@/lib/api";
import type { MetaResponse } from "@/lib/types";

// always render fresh from the rollup API
export const dynamic = "force-dynamic";

function Tabs({ game, format }: { game: string; format: string }) {
  return (
    <nav className="tabs">
      {KNOWN_FORMATS.map((f) => {
        const active = f.game === game && f.format === format;
        return (
          <a
            key={`${f.game}/${f.format}`}
            className={active ? "tab active" : "tab"}
            href={`/${f.game}/${f.format}`}
          >
            {f.label}
          </a>
        );
      })}
    </nav>
  );
}

export default async function MetaPage({
  params,
}: {
  params: { game: string; format: string };
}) {
  const { game, format } = params;

  let meta: MetaResponse | null = null;
  let error: string | null = null;
  try {
    meta = await getMeta(game, format);
  } catch (e) {
    error =
      e instanceof ApiError && e.status === 404
        ? `No data for ${game}/${format} yet.`
        : "Could not reach the read API.";
  }

  return (
    <main className="container">
      <header className="app">
        <div className="brand">
          Meta<span>Surf</span>
        </div>
        {meta && <div className="subhead">as of {meta.as_of}</div>}
      </header>
      <p className="subhead">Metagame snapshot — share &amp; winrate</p>

      <Tabs game={game} format={format} />

      {error ? (
        <div className="error">
          <strong>{error}</strong>
          <p className="foot" style={{ marginTop: 8 }}>
            Start the read API in dev:{" "}
            <code>uvicorn api.app:app --reload --port 8000</code>, and set{" "}
            <code>API_BASE</code> in <code>web/.env.local</code>.
          </p>
        </div>
      ) : (
        meta && (
          <>
            <MetaTable archetypes={meta.archetypes} />

            <LockedPanel title="Share &amp; winrate trends">
              See how each archetype&apos;s share and winrate have moved
              week-over-week, with statistical confidence — plus rising/falling
              movers and the emerging-deck feed.
            </LockedPanel>

            <p className="foot">
              {meta.archetypes.length} archetypes · {game}/{format}. Winrates
              show a 95% credible interval; coloured only when the interval
              clears 50%. Data from precomputed rollups.
            </p>
          </>
        )
      )}
    </main>
  );
}
