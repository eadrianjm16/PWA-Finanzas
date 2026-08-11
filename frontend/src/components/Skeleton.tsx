export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-surface-hover ${className}`} />;
}

export function SkeletonList({ rows = 4 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-[var(--shadow-card)]">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`flex items-center justify-between px-4 py-3.5 ${i > 0 ? "border-t border-surface-border" : ""}`}
        >
          <div className="flex items-center gap-3">
            <Skeleton className="h-9 w-9 rounded-full" />
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="h-2.5 w-16" />
            </div>
          </div>
          <Skeleton className="h-3.5 w-14" />
        </div>
      ))}
    </div>
  );
}
