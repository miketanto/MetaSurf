import { Nav } from "@/components/Nav";
import { ArchetypeTabs } from "@/components/ArchetypeTabs";
import { MatchupBreakdown } from "@/components/MatchupBreakdown";
import { getMatchups, ApiError } from "@/lib/api";
import type { MatchupsResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ArchetypeMatchupsPage({
  params,
}: {
  params: { game: string; format: string; id: string };
}) {
  const { game, format } = params;
  const id = Number(params.id);

  let m: MatchupsResponse | null = null;
  let error: string | null = null;
  try {
    m = await getMatchups(game, format);
  } catch (e) {
    error = e instanceof ApiError ? "No data." : "Could not reach the API.";
  }

  const name = m?.archetypes.find((a) => a.archetype_id === id)?.name ?? null;
  const hasSpread =
    m != null && m.cells.some((c) => c.arch_a === id && c.arch_b !== id && c.n_matches > 0);

  return (
    <main className="container">
      <Nav game={game} format={format} section="meta" asOf={m?.as_of} />
      <a className="back" href={`/${game}/${format}`}>
        ‹ Meta
      </a>
      {error || !m || !name ? (
        <div className="error">
          <strong>{error ?? "No matchup data for this archetype."}</strong>
        </div>
      ) : (
        <>
          <h1 className="deck-title">{name}</h1>
          <ArchetypeTabs game={game} format={format} id={id} active="matchups" />
          <p className="subhead">Matchup spread — best to worst</p>
          {hasSpread ? (
            <MatchupBreakdown m={m} focusId={id} game={game} format={format} />
          ) : (
            <div className="error">No matchup data for this archetype in this snapshot.</div>
          )}
        </>
      )}
    </main>
  );
}
