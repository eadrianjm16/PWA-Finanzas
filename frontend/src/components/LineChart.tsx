interface LinePoint {
  date: string;
  value: number;
}

const WIDTH = 300;
const HEIGHT = 100;
const PADDING = 6;

export default function LineChart({ points }: { points: LinePoint[] }) {
  if (points.length < 2) {
    return <p className="py-8 text-center text-sm text-muted">Aún no hay suficiente historial para dibujar el gráfico.</p>;
  }

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const coords = points.map((p, i) => {
    const x = PADDING + (i / (points.length - 1)) * (WIDTH - PADDING * 2);
    const y = HEIGHT - PADDING - ((p.value - min) / range) * (HEIGHT - PADDING * 2);
    return { x, y };
  });

  const linePath = coords.map((c) => `${c.x},${c.y}`).join(" ");
  const areaPath = `${PADDING},${HEIGHT - PADDING} ${linePath} ${WIDTH - PADDING},${HEIGHT - PADDING}`;

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-28 w-full" preserveAspectRatio="none">
      <polygon points={areaPath} fill="var(--brand-soft)" opacity="0.6" />
      <polyline points={linePath} fill="none" stroke="var(--brand)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={coords[coords.length - 1].x} cy={coords[coords.length - 1].y} r="3" fill="var(--brand)" />
    </svg>
  );
}
