import { Nav } from "@/components/Nav";
import { MatchupBreakdown } from "@/components/MatchupBreakdown";
import { DeckList } from "@/components/DeckList";
import { LockedPanel } from "@/components/LockedPanel";
import { getMeta, getMatchups, getArchetypeDecks, ApiError } from "@/lib/api";
import { pctInt } from "@/lib/matchup";
import type { DeckSummary, MatchupsResponse, MetaArchetype } from "@/lib/types";

export const dynamic = "force-dynamic";

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

export default async function ArchetypePage({
  params,
}: {
  params: { game: string; format: string; id: string };
}) {
  const { game, format } = params;
  const id = Number(params.id);

  let m: MatchupsResponse | null = null;
  let stat: MetaArchetype | undefined;
  let decks: DeckSummary[] = [];
  let name: string | null = null;
  let notFound = false;

  const [metaRes, matchRes, decksRes] = await Promise.allSettled([
    getMeta(game, format),
    getMatchups(game, format),
    getArchetypeDecks(game, format, id, 25),
  ]);

  if (metaRes.status === "fulfilled") {
    stat = metaRes.value.archetypes.find((a) => a.archetype_id === id);
    if (stat) name = stat.name;
  }
  if (matchRes.status === "fulfilled") {
    m = matchRes.value;
    name = name ?? m.archetypes.find((a) => a.archetype_id === id)?.name ?? null;
  }
  if (decksRes.status === "fulfilled") {
    decks = decksRes.value.decks;
    name = name ?? decksRes.value.name;
  } else if (
    decksRes.reason instanceof ApiError &&
    decksRes.reason.status === 404
  ) {
    notFound = !name;
  }

  const spread = m
    ? m.cells
        .filter((c) => c.arch_a === id && c.arch_b !== id && c.n_matches > 0)
        .sort((a, b) => b.p_a_beats_b - a.p_a_beats_b)
    : [];
  const best = spread.slice(0, 3);
  const names = new Map((m?.archetypes ?? []).map((a) => [a.archetype_id, a.name]));

  return (
    <main className="container">
      <Nav game={game} format={format} section="meta" asOf={m?.as_of} />
      <a className="back" href={`/${game}/${format}`}>
        ‹ Meta
      </a>

      {notFound || !name ? (
        <div className="error">
          <strong>Unknown archetype.</strong>
        </div>
      ) : (
        <>
          <h1 className="deck-title">{name}</h1>

          {stat && (
            <div className="stats">
              <div className="stat">
                <div className="stat-lbl">Win rate</div>
                <div className="stat-val">{pct(stat.winrate)}</div>
                <div className="stat-sub">
                  {pct(stat.wr_ci_lo)}–{pct(stat.wr_ci_hi)}
                </div>
              </div>
              <div className="stat">
                <div className="stat-lbl">Meta share</div>
                <div className="stat-val">{pct(stat.share)}</div>
                <div className="stat-sub">{stat.n_decks} decks</div>
              </div>
            </div>
          )}

          {best.length > 0 && (
            <>
              <p className="subhead">Best matchups</p>
              <div className="chips">
                {best.map((c) => (
                  <a
                    key={c.arch_b}
                    className="chip"
                    href={`/${game}/${format}/archetypes/${c.arch_b}`}
                  >
                    {names.get(c.arch_b)} <b>{pctInt(c.p_a_beats_b)}%</b>
                  </a>
                ))}
              </div>
            </>
          )}

          {m && spread.length > 0 && (
            <>
              <p className="subhead" style={{ marginTop: 20 }}>
                Matchup spread — best to worst
              </p>
              <MatchupBreakdown m={m} focusId={id} game={game} format={format} />
            </>
          )}

          <p className="subhead" style={{ marginTop: 22 }}>
            Recent decklists {decks.length > 0 && <span className="muted">({decks.length})</span>}
          </p>
          {decks.length > 0 ? (
            <DeckList decks={decks} game={game} format={format} />
          ) : (
            <div className="error">No stored decklists for this archetype yet.</div>
          )}

          <LockedPanel title="Price, colors &amp; card-choice trends">
            Average price, color breakdown, and how this archetype&apos;s card
            choices have shifted week to week.
          </LockedPanel>
        </>
      )}
    </main>
  );
}
