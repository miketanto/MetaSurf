import type { MetaArchetype } from "@/lib/types";
import { Sparkline } from "./Sparkline";

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

function wrClass(a: MetaArchetype): string {
  // colour only when the CI clears 50% either way; otherwise neutral
  if (a.wr_ci_lo > 0.5) return "wr good";
  if (a.wr_ci_hi < 0.5) return "wr bad";
  return "wr";
}

export function MetaTable({ archetypes }: { archetypes: MetaArchetype[] }) {
  const sorted = [...archetypes].sort((a, b) => b.share - a.share);
  return (
    <div className="card" role="table" aria-label="Metagame share and winrate">
      {sorted.map((a) => (
        <div className="row" role="row" key={a.archetype_id}>
          <div className="name">
            <div className="title">{a.name}</div>
            <div className="meta">
              {a.n_decks} decks · <Sparkline values={a.sparkline} />
            </div>
          </div>
          <div className="share">{pct(a.share)}</div>
          <div className={wrClass(a)}>
            <div className="val">{pct(a.winrate)}</div>
            <div className="ci">
              {pct(a.wr_ci_lo)}–{pct(a.wr_ci_hi)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
