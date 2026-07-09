const COLOR: Record<string, { bg: string; fg: string }> = {
  W: { bg: "#f4eecf", fg: "#6b6437" },
  U: { bg: "#3b7bd0", fg: "#eaf2fd" },
  B: { bg: "#2b2b33", fg: "#c9c4d2" },
  R: { bg: "#d3492f", fg: "#fdeae6" },
  G: { bg: "#3e9c62", fg: "#e9f7ee" },
  C: { bg: "#8a919e", fg: "#12151b" },
};
const ORDER = "WUBRGC";

// WUBRG mana pips for a deck/archetype. Empty -> a single colorless pip.
export function ColorPips({ colors }: { colors: string[] }) {
  const list = colors.length === 0 ? ["C"] : [...colors];
  list.sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b));
  return (
    <span className="pips" aria-label={`colors: ${list.join("")}`}>
      {list.map((c) => {
        const s = COLOR[c] ?? COLOR.C;
        return (
          <span key={c} className="pip" style={{ background: s.bg, color: s.fg }}>
            {c}
          </span>
        );
      })}
    </span>
  );
}
