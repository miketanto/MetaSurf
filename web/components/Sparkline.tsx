// Tiny inline SVG sparkline of weekly share. No deps.

export function Sparkline({
  values,
  width = 64,
  height = 22,
}: {
  values: number[];
  width?: number;
  height?: number;
}) {
  if (values.length < 2) {
    // one data week — a flat baseline dash, not a misleading line
    return (
      <svg width={width} height={height} aria-hidden="true">
        <line
          x1={2}
          y1={height - 3}
          x2={width - 2}
          y2={height - 3}
          stroke="var(--border)"
          strokeWidth={2}
        />
      </svg>
    );
  }
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const stepX = (width - 4) / (values.length - 1);
  const pts = values.map((v, i) => {
    const x = 2 + i * stepX;
    const y = 2 + (height - 4) * (1 - (v - min) / span);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const rising = values[values.length - 1] >= values[0];
  return (
    <svg width={width} height={height} aria-hidden="true">
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={rising ? "var(--good)" : "var(--bad)"}
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
