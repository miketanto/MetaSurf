import type { MatchupAxis, MatchupsResponse } from "@/lib/types";
import {
  cellIndex,
  code,
  confidence,
  confidenceOpacity,
  pctInt,
  tint,
} from "@/lib/matchup";

const CELL = 34; // px
const NAMECOL = 116; // px

// Row = "your deck", cell = P(row deck beats column deck). Green favoured, red
// against, faded when the sample is thin. Tap a row to drill into that deck.
export function MatchupGrid({
  m,
  order,
  game,
  format,
}: {
  m: MatchupsResponse;
  order: MatchupAxis[];
  game: string;
  format: string;
}) {
  const idx = cellIndex(m);
  const width = NAMECOL + order.length * CELL;

  return (
    <div>
      <div className="grid-scroll">
        <div className="grid" style={{ width }}>
          <div className="grid-head" style={{ height: CELL }}>
            <div className="corner" style={{ width: NAMECOL }} />
            {order.map((a) => (
              <div className="colhead" style={{ width: CELL }} key={a.archetype_id}>
                {code(a.name)}
              </div>
            ))}
          </div>

          {order.map((row) => (
            <a
              className="grid-row"
              key={row.archetype_id}
              href={`/${game}/${format}/matchups/${row.archetype_id}`}
            >
              <div className="rowname" style={{ width: NAMECOL }}>
                {row.name}
                <span className="chev">›</span>
              </div>
              {order.map((col) => {
                if (row.archetype_id === col.archetype_id) {
                  return (
                    <div className="cell mirror" style={{ width: CELL }} key={col.archetype_id}>
                      –
                    </div>
                  );
                }
                const c = idx.get(`${row.archetype_id}:${col.archetype_id}`);
                if (!c || c.n_matches === 0) {
                  return (
                    <div className="cell empty" style={{ width: CELL }} key={col.archetype_id} />
                  );
                }
                return (
                  <div
                    className="cell"
                    style={{
                      width: CELL,
                      background: tint(c.p_a_beats_b),
                      opacity: confidenceOpacity[confidence(c.n_matches)],
                    }}
                    key={col.archetype_id}
                  >
                    {pctInt(c.p_a_beats_b)}
                  </div>
                );
              })}
            </a>
          ))}
        </div>
      </div>

      <div className="legend">
        {order.map((a) => (
          <span className="legend-item" key={a.archetype_id}>
            <b>{code(a.name)}</b> {a.name}
          </span>
        ))}
      </div>
    </div>
  );
}
