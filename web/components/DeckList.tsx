import type { DeckSummary } from "@/lib/types";
import { record, finishBadge } from "@/lib/deckmeta";
import { ColorPips } from "./ColorPips";

export function DeckList({
  decks,
  game,
  format,
}: {
  decks: DeckSummary[];
  game: string;
  format: string;
}) {
  if (decks.length === 0) {
    return <div className="error">No decklists match.</div>;
  }
  return (
    <div className="card">
      {decks.map((d) => {
        const badge = finishBadge(d);
        return (
          <a
            className="drow"
            key={d.deck_id}
            href={`/${game}/${format}/decks/${d.deck_id}`}
          >
            <div className="dinfo">
              <div className="dplayer">
                {d.player ?? "Unknown pilot"}
                {badge && <span className="badge">{badge}</span>}
              </div>
              <div className="dmeta">
                <ColorPips colors={d.colors} /> {d.event ?? d.source} · {d.date}
              </div>
            </div>
            <div className="drec">{record(d)}</div>
            <div className="chev">›</div>
          </a>
        );
      })}
    </div>
  );
}
