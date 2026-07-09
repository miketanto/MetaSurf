import { Nav } from "@/components/Nav";
import { ExportBar } from "@/components/ExportBar";
import { ColorPips } from "@/components/ColorPips";
import { getDeck, ApiError } from "@/lib/api";
import { groupByType, countOf } from "@/lib/cardtypes";
import type { DeckCard, DeckDetailResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

function record(d: DeckDetailResponse): string {
  if (d.wins != null && d.losses != null) return `${d.wins}–${d.losses}`;
  if (d.finish_rank != null) return `Finish #${d.finish_rank}`;
  return "";
}

function CardRows({ cards }: { cards: DeckCard[] }) {
  return (
    <>
      {cards.map((c) => (
        <div className="crow" key={c.name}>
          <span className="cnt">{c.count}</span>
          <span className="cname">{c.name}</span>
          {c.colors.length > 0 && <ColorPips colors={c.colors} />}
        </div>
      ))}
    </>
  );
}

function TypeSection({ title, cards }: { title: string; cards: DeckCard[] }) {
  return (
    <div className="typesec">
      <div className="typesec-head">
        {title} <span>[{countOf(cards)}]</span>
      </div>
      <CardRows cards={cards} />
    </div>
  );
}

export default async function DeckDetailPage({
  params,
}: {
  params: { game: string; format: string; deck: string };
}) {
  const { game, format } = params;
  const deckId = Number(params.deck);

  let d: DeckDetailResponse | null = null;
  let error: string | null = null;
  try {
    d = await getDeck(game, format, deckId);
  } catch (e) {
    error = e instanceof ApiError && e.status === 404 ? "Deck not found." : "Could not reach the API.";
  }

  const main = d ? d.cards.filter((c) => c.board !== "side") : [];
  const side = d ? d.cards.filter((c) => c.board === "side") : [];

  return (
    <main className="container">
      <Nav game={game} format={format} section="matchups" />

      {error || !d ? (
        <div className="error">
          <strong>{error ?? "Not found."}</strong>
        </div>
      ) : (
        <>
          <a className="back" href={`/${game}/${format}/archetypes/${d.archetype_id}`}>
            ‹ {d.name ?? "Archetype"}
          </a>
          <div className="titlerow">
            <h1 className="deck-title">{d.name ?? "Decklist"}</h1>
            <ColorPips colors={d.colors} />
          </div>
          <p className="subhead">
            {d.player ?? "Unknown pilot"} · {d.event ?? d.source} · {d.date}
            {record(d) && <> · {record(d)}</>}
          </p>

          <ExportBar cards={d.cards} />

          <div className="deckcols">
            <div className="card deckpane">
              <div className="pane-head">
                Maindeck <span>({countOf(main)})</span>
              </div>
              {groupByType(main).map(([t, cs]) => (
                <TypeSection key={t} title={t} cards={cs} />
              ))}
            </div>
            {side.length > 0 && (
              <div className="card deckpane">
                <div className="pane-head">
                  Sideboard <span>({countOf(side)})</span>
                </div>
                <CardRows
                  cards={[...side].sort(
                    (a, b) => b.count - a.count || a.name.localeCompare(b.name),
                  )}
                />
              </div>
            )}
          </div>

          <p className="foot">Source: {d.source}. Exact list as recorded.</p>
        </>
      )}
    </main>
  );
}
