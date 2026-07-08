"use client";

import { useMemo, useState } from "react";
import type { DeckSummary } from "@/lib/types";
import { DeckList } from "./DeckList";
import { winPct } from "@/lib/deckmeta";

type Finish = "all" | "winners" | "top8";
type Sort = "new" | "finish" | "record";

export function DecksBrowser({
  decks,
  game,
  format,
}: {
  decks: DeckSummary[];
  game: string;
  format: string;
}) {
  const [finish, setFinish] = useState<Finish>("all");
  const [source, setSource] = useState<string>("all");
  const [sort, setSort] = useState<Sort>("new");

  const sources = useMemo(
    () => Array.from(new Set(decks.map((d) => d.source))).sort(),
    [decks],
  );

  const view = useMemo(() => {
    let v = decks.slice();
    if (source !== "all") v = v.filter((d) => d.source === source);
    if (finish === "winners")
      v = v.filter((d) => d.finish_rank === 1 || (d.wins != null && d.losses === 0));
    if (finish === "top8")
      v = v.filter((d) => d.finish_rank != null && d.finish_rank <= 8);
    v.sort((a, b) => {
      if (sort === "new") return a.date < b.date ? 1 : a.date > b.date ? -1 : b.deck_id - a.deck_id;
      if (sort === "finish") {
        const ra = a.finish_rank ?? 9999;
        const rb = b.finish_rank ?? 9999;
        return ra !== rb ? ra - rb : winPct(b) - winPct(a);
      }
      return winPct(b) - winPct(a);
    });
    return v;
  }, [decks, finish, source, sort]);

  const pill = (k: Finish, label: string) => (
    <button className={finish === k ? "pill on" : "pill"} onClick={() => setFinish(k)}>
      {label}
    </button>
  );

  return (
    <div>
      <div className="filters">
        <div className="pillrow">
          {pill("all", "All")}
          {pill("winners", "Winners")}
          {pill("top8", "Top 8")}
        </div>
        <div className="selrow">
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="all">All sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
            <option value="new">Newest</option>
            <option value="finish">Best finish</option>
            <option value="record">Best record</option>
          </select>
        </div>
      </div>
      <div className="count">
        {view.length} deck{view.length === 1 ? "" : "s"}
      </div>
      <DeckList decks={view} game={game} format={format} />
    </div>
  );
}
