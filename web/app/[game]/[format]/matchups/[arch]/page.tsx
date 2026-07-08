import { Nav } from "@/components/Nav";
import { MatchupBreakdown } from "@/components/MatchupBreakdown";
import { DeckList } from "@/components/DeckList";
import { LockedPanel } from "@/components/LockedPanel";
import { getMatchups, getArchetypeDecks, ApiError } from "@/lib/api";
import { pctInt } from "@/lib/matchup";
import type { MatchupsResponse, DeckSummary } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function DeckMatchupsPage({
  params,
}: {
  params: { game: string; format: string; arch: string };
}) {
  const { game, format } = params;
  const focusId = Number(params.arch);

  let m: MatchupsResponse | null = null;
  let error: string | null = null;
  try {
    m = await getMatchups(game, format);
  } catch (e) {
    error = e instanceof ApiError ? "No data for this snapshot." : "Could not reach the read API.";
  }

  const name = m?.archetypes.find((a) => a.archetype_id === focusId)?.name;
  const spread = m
    ? m.cells
        .filter((c) => c.arch_a === focusId && c.arch_b !== focusId && c.n_matches > 0)
        .sort((a, b) => b.p_a_beats_b - a.p_a_beats_b)
    : [];
  const best = spread[0];
  const worst = spread[spread.length - 1];
  const names = new Map((m?.archetypes ?? []).map((a) => [a.archetype_id, a.name]));

  let decks: DeckSummary[] = [];
  try {
    decks = (await getArchetypeDecks(game, format, focusId, 8)).decks;
  } catch {
    decks = [];
  }

  return (
    <main className="container">
      <Nav game={game} format={format} section="matchups" asOf={m?.as_of} />

      <a className="back" href={`/${game}/${format}/matchups`}>
        ‹ All matchups
      </a>

      {error || !m ? (
        <div className="error">
          <strong>{error ?? "Not found."}</strong>
        </div>
      ) : (
        <>
          <h1 className="deck-title">{name ?? `Deck ${focusId}`}</h1>

          {best && worst && (
            <div className="summary">
              <div className="summary-cell good">
                <div className="lbl">Best into</div>
                <div className="val">{names.get(best.arch_b)}</div>
                <div className="num">{pctInt(best.p_a_beats_b)}%</div>
              </div>
              <div className="summary-cell bad">
                <div className="lbl">Worst into</div>
                <div className="val">{names.get(worst.arch_b)}</div>
                <div className="num">{pctInt(worst.p_a_beats_b)}%</div>
              </div>
            </div>
          )}

          <p className="subhead">Matchup spread — best to worst</p>
          <MatchupBreakdown m={m} focusId={focusId} />

          {decks.length > 0 && (
            <>
              <p className="subhead" style={{ marginTop: 22 }}>
                Recent decklists
              </p>
              <DeckList decks={decks} game={game} format={format} />
            </>
          )}

          <LockedPanel title="What to bring">
            The sideboard tech that swings this deck&apos;s toughest matchups,
            from cross-field card data.
          </LockedPanel>
        </>
      )}
    </main>
  );
}
