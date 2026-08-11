import { formatMoney } from "@/lib/format";

interface DonutSegment {
  id: string;
  label: string;
  value: number;
  color: string;
}

export default function DonutChart({
  segments,
  onSelect,
}: {
  segments: DonutSegment[];
  onSelect?: (id: string) => void;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const gap = total > 0 ? circumference * 0.008 : 0;
  let cumulative = 0;

  return (
    <div className="flex items-center gap-6">
      <div className="relative h-32 w-32 shrink-0">
        <svg viewBox="0 0 160 160" className="h-32 w-32 -rotate-90">
          <circle cx="80" cy="80" r={radius} fill="none" stroke="var(--surface-hover)" strokeWidth="18" />
          {total > 0 &&
            segments.map((segment) => {
              const dash = Math.max((segment.value / total) * circumference - gap, 0);
              const dashOffset = -cumulative;
              cumulative += dash + gap;
              return (
                <circle
                  key={segment.id}
                  cx="80"
                  cy="80"
                  r={radius}
                  fill="none"
                  stroke={segment.color}
                  strokeWidth="18"
                  strokeLinecap="round"
                  strokeDasharray={`${dash} ${circumference - dash}`}
                  strokeDashoffset={dashOffset}
                />
              );
            })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[10px] font-medium text-muted-soft">Total</span>
          <span className="tabular-nums text-sm font-semibold">{formatMoney(total, "EUR")}</span>
        </div>
      </div>
      <ul className="flex-1 space-y-2">
        {segments.map((segment) => (
          <li key={segment.id}>
            <button
              onClick={() => onSelect?.(segment.id)}
              className="flex w-full items-center gap-2 rounded-lg text-left text-xs transition hover:bg-surface-hover"
            >
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: segment.color }} />
              <span className="flex-1 truncate font-medium">{segment.label}</span>
              <span className="tabular-nums text-muted">
                {total > 0 ? Math.round((segment.value / total) * 100) : 0}%
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
