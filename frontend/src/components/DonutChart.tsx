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
  let cumulative = 0;

  return (
    <div className="flex items-center gap-6">
      <svg viewBox="0 0 160 160" className="h-32 w-32 shrink-0 -rotate-90">
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          stroke="currentColor"
          className="text-neutral-100 dark:text-neutral-800"
          strokeWidth="20"
        />
        {total > 0 &&
          segments.map((segment) => {
            const dash = (segment.value / total) * circumference;
            const dashOffset = -cumulative;
            cumulative += dash;
            return (
              <circle
                key={segment.id}
                cx="80"
                cy="80"
                r={radius}
                fill="none"
                stroke={segment.color}
                strokeWidth="20"
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={dashOffset}
              />
            );
          })}
      </svg>
      <ul className="flex-1 space-y-1.5">
        {segments.map((segment) => (
          <li key={segment.id}>
            <button onClick={() => onSelect?.(segment.id)} className="flex w-full items-center gap-2 text-left text-xs">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: segment.color }} />
              <span className="flex-1 truncate">{segment.label}</span>
              <span className="text-neutral-500">{total > 0 ? Math.round((segment.value / total) * 100) : 0}%</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
