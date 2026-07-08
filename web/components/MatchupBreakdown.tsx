import type { MatchupsResponse } from "@/lib/types";
import { confidence, pctInt, tint } from "@/lib/matchup";

const DOT: Record<string, string> = { high: "●", med: "◐", low: "○" };

// One deck's matchup spread: every opponent it has data against, best → worst.
// Each opponent links to its own archetype page.
export function MatchupBreakdown({
  m,
  focusId,
  game,
  format,
}: {
  m: MatchupsResponse;
  focusId: number;
  game: string;
  format: string;
}) {
  const names = new Map(m.archetypes.map((a) => [a.archetype_id, a.name]));
  const rows = m.cells
    .filter(
      (c) => c.arch_a === focusId && c.arch_b !== focusId && c.n_matches > 0,
    )
    .sort((a, b) => b.p_a_beats_b - a.p_a_beats_b);

  if (rows.length === 0) {
    return <div className="error">No matchup data for this deck in this snapshot.</div>;
  }

  return (
    <div className="card">
      {rows.map((c) => {
        const conf = confidence(c.n_matches);
        return (
          <a
            className="mrow"
            key={c.arch_b}
            href={`/${game}/${format}/archetypes/${c.arch_b}`}
          >
            <div className="mname">{names.get(c.arch_b) ?? c.arch_b}</div>
            <div
              className="mchip"
              style={{ background: tint(c.p_a_beats_b) }}
              title={`${pctInt(c.ci_lo)}–${pctInt(c.ci_hi)}% CI`}
            >
              {pctInt(c.p_a_beats_b)}%
            </div>
            <div className="mmeta">
              <span className={`dot ${conf}`}>{DOT[conf]}</span>
              {c.n_matches} games
            </div>
          </a>
        );
      })}
    </div>
  );
}
