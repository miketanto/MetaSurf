import { Nav } from "@/components/Nav";
import { ExportBar } from "@/components/ExportBar";
import { ColorPips } from "@/components/ColorPips";
import { getDeck, ApiError } from "@/lib/api";
import type { DeckDetailResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

function record(d: DeckDetailResponse): string {
  if (d.wins != null && d.losses != null) return `${d.wins}–${d.losses}`;
  if (d.finish_rank != null) return `Finish #${d.finish_rank}`;
  return "";
}

function Zone({ title, cards }: { title: string; cards: { name: string; count: number }[] }) {
  if (cards.length === 0) return null;
  const total = cards.reduce((s, c) => s + c.count, 0);
  return (
    <div className="zone">
      <div className="zone-head">
        {title} <span>{total}</span>
      </div>
      <div className="card">
        {cards.map((c) => (
          <div className="crow" key={c.name}>
            <span className="cnt">{c.count}</span>
            <span className="cname">{c.name}</span>
          </div>
        ))}
      </div>
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

          <div style={{ marginTop: 18 }}>
            <Zone title="Mainboard" cards={d.cards.filter((c) => c.board !== "side")} />
            <Zone title="Sideboard" cards={d.cards.filter((c) => c.board === "side")} />
          </div>

          <p className="foot">Source: {d.source}. Exact list as recorded.</p>
        </>
      )}
    </main>
  );
}
