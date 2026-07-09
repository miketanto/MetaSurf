import { Nav } from "@/components/Nav";
import { ArchetypeTabs } from "@/components/ArchetypeTabs";
import { DeckList } from "@/components/DeckList";
import { ColorPips } from "@/components/ColorPips";
import { LockedPanel } from "@/components/LockedPanel";
import { getMeta, getMatchups, getArchetypeDecks, ApiError } from "@/lib/api";
import { pctInt } from "@/lib/matchup";
import { isNotable } from "@/lib/deckmeta";
import type { DeckSummary, MatchupsResponse, MetaArchetype } from "@/lib/types";

export const dynamic = "force-dynamic";

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

export default async function ArchetypeOverview({
  params,
}: {
  params: { game: string; format: string; id: string };
}) {
  const { game, format } = params;
  const id = Number(params.id);

  const [metaRes, matchRes, decksRes] = await Promise.allSettled([
    getMeta(game, format),
    getMatchups(game, format),
    getArchetypeDecks(game, format, id, 40),
  ]);

  let stat: MetaArchetype | undefined;
  let m: MatchupsResponse | null = null;
  let decks: DeckSummary[] = [];
  let archColors: string[] = [];
  let name: string | null = null;

  if (metaRes.status === "fulfilled") {
    stat = metaRes.value.archetypes.find((a) => a.archetype_id === id);
    name = stat?.name ?? null;
  }
  if (matchRes.status === "fulfilled") {
    m = matchRes.value;
    name = name ?? m.archetypes.find((a) => a.archetype_id === id)?.name ?? null;
  }
  if (decksRes.status === "fulfilled") {
    decks = decksRes.value.decks;
    archColors = decksRes.value.colors;
    name = name ?? decksRes.value.name;
  }
  const unknown =
    !name &&
    decksRes.status === "rejected" &&
    decksRes.reason instanceof ApiError &&
    decksRes.reason.status === 404;

  const spread = m
    ? m.cells
        .filter((c) => c.arch_a === id && c.arch_b !== id && c.n_matches > 0)
        .sort((a, b) => b.p_a_beats_b - a.p_a_beats_b)
    : [];
  const names = new Map((m?.archetypes ?? []).map((a) => [a.archetype_id, a.name]));
  const notable = decks.filter(isNotable).slice(0, 6);
  const recent = decks.slice(0, 5);

  return (
    <main className="container">
      <Nav game={game} format={format} section="meta" asOf={m?.as_of} />
      <a className="back" href={`/${game}/${format}`}>
        ‹ Meta
      </a>

      {unknown || !name ? (
        <div className="error">
          <strong>Unknown archetype.</strong>
        </div>
      ) : (
        <>
          <div className="titlerow">
            <h1 className="deck-title">{name}</h1>
            <ColorPips colors={archColors} />
          </div>
          <ArchetypeTabs game={game} format={format} id={id} active="overview" />

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

          {spread.length > 0 && (
            <>
              <p className="subhead">Best matchups</p>
              <div className="chips">
                {spread.slice(0, 3).map((c) => (
                  <a
                    key={c.arch_b}
                    className="chip"
                    href={`/${game}/${format}/archetypes/${c.arch_b}`}
                  >
                    {names.get(c.arch_b)} <b>{pctInt(c.p_a_beats_b)}%</b>
                  </a>
                ))}
                <a className="chip more" href={`/${game}/${format}/archetypes/${id}/matchups`}>
                  all matchups ›
                </a>
              </div>
            </>
          )}

          {notable.length > 0 && (
            <>
              <p className="subhead" style={{ marginTop: 20 }}>
                Notable performances
              </p>
              <DeckList decks={notable} game={game} format={format} />
            </>
          )}

          {recent.length > 0 && (
            <>
              <div className="rowhead">
                <span className="subhead" style={{ margin: 0 }}>
                  Recent decks
                </span>
                <a className="seeall" href={`/${game}/${format}/archetypes/${id}/decks`}>
                  All decks ›
                </a>
              </div>
              <DeckList decks={recent} game={game} format={format} />
            </>
          )}

          <LockedPanel title="New tech watch">
            Cards breaking into {name} lately, and the tech other decks are
            packing against it — from cross-field card data.
          </LockedPanel>
        </>
      )}
    </main>
  );
}
