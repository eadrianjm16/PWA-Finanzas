import { formatShortMonth } from "@/lib/format";
import type { MonthTotals } from "@/lib/types";

export default function BarChart({ data }: { data: MonthTotals[] }) {
  const max = Math.max(1, ...data.flatMap((d) => [d.income, d.expense]));

  return (
    <div className="flex items-end justify-between gap-2">
      {data.map((d) => (
        <div key={d.month} className="flex flex-1 flex-col items-center gap-1">
          <div className="flex h-24 w-full items-end justify-center gap-0.5">
            <div
              className="w-2.5 rounded-t bg-emerald-500"
              style={{ height: `${(d.income / max) * 100}%` }}
              title={`Ingresos: ${d.income.toFixed(2)}`}
            />
            <div
              className="w-2.5 rounded-t bg-neutral-400 dark:bg-neutral-600"
              style={{ height: `${(d.expense / max) * 100}%` }}
              title={`Gastos: ${d.expense.toFixed(2)}`}
            />
          </div>
          <span className="text-[10px] text-neutral-500">{formatShortMonth(d.month)}</span>
        </div>
      ))}
    </div>
  );
}
