import type { DeckSummary } from "@/lib/types";

function record(d: DeckSummary): string {
  if (d.wins != null && d.losses != null) return `${d.wins}–${d.losses}`;
  if (d.finish_rank != null) return `#${d.finish_rank}`;
  return "";
}

export function DeckList({
  decks,
  game,
  format,
}: {
  decks: DeckSummary[];
  game: string;
  format: string;
}) {
  return (
    <div className="card">
      {decks.map((d) => (
        <a
          className="drow"
          key={d.deck_id}
          href={`/${game}/${format}/decks/${d.deck_id}`}
        >
          <div className="dinfo">
            <div className="dplayer">{d.player ?? "Unknown pilot"}</div>
            <div className="dmeta">
              {d.event ?? d.source} · {d.date}
            </div>
          </div>
          <div className="drec">{record(d)}</div>
          <div className="chev">›</div>
        </a>
      ))}
    </div>
  );
}
