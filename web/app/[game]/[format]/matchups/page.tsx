import { Nav } from "@/components/Nav";
import { MatchupGrid } from "@/components/MatchupGrid";
import { LockedPanel } from "@/components/LockedPanel";
import { getMatchups, getMeta, ApiError } from "@/lib/api";
import type { MatchupAxis, MatchupsResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

const TOP_N = 8; // archetypes shown in the grid (mobile-readable)

// order the matchup axis by metagame share (biggest decks first), top N
async function topOrder(
  game: string,
  format: string,
  axis: MatchupAxis[],
): Promise<MatchupAxis[]> {
  try {
    const meta = await getMeta(game, format);
    const share = new Map(meta.archetypes.map((a) => [a.archetype_id, a.share]));
    return [...axis]
      .filter((a) => share.has(a.archetype_id))
      .sort((a, b) => (share.get(b.archetype_id) ?? 0) - (share.get(a.archetype_id) ?? 0))
      .slice(0, TOP_N);
  } catch {
    return axis.slice(0, TOP_N);
  }
}

export default async function MatchupsPage({
  params,
}: {
  params: { game: string; format: string };
}) {
  const { game, format } = params;

  let m: MatchupsResponse | null = null;
  let error: string | null = null;
  try {
    m = await getMatchups(game, format);
  } catch (e) {
    error =
      e instanceof ApiError && e.status === 404
        ? `No matchup data for ${game}/${format} yet.`
        : "Could not reach the read API.";
  }

  const order = m ? await topOrder(game, format, m.archetypes) : [];

  return (
    <main className="container">
      <Nav game={game} format={format} section="matchups" asOf={m?.as_of} />
      <p className="subhead">
        Win rate of the <b>row</b> deck vs the <b>column</b> deck. Tap a deck for
        its full spread.
      </p>

      {error ? (
        <div className="error">
          <strong>{error}</strong>
        </div>
      ) : (
        m && (
          <>
            <MatchupGrid m={m} order={order} game={game} format={format} />

            <div className="confkey">
              <span>
                <span className="dot high">●</span> 100+ games
              </span>
              <span>
                <span className="dot med">◐</span> 30+
              </span>
              <span>
                <span className="dot low">○</span> few — faded
              </span>
            </div>

            <LockedPanel title="Matchup history &amp; sideboard plans">
              See how each matchup has shifted week to week (&quot;this flipped
              when they adopted card X&quot;) and the card-by-card sideboard
              breakdown per pairing.
            </LockedPanel>

            <p className="foot">
              Top {order.length} decks by share, {game}/{format}. Cells tint by
              win probability; faded cells have small samples. Numbers are the
              posterior estimate; tap a deck for confidence intervals.
            </p>
          </>
        )
      )}
    </main>
  );
}
