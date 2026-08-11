import { formatShortMonth } from "@/lib/format";
import type { MonthTotals } from "@/lib/types";

export default function BarChart({ data }: { data: MonthTotals[] }) {
  const max = Math.max(1, ...data.flatMap((d) => [d.income, d.expense]));

  return (
    <div className="flex items-end justify-between gap-2">
      {data.map((d) => (
        <div key={d.month} className="flex flex-1 flex-col items-center gap-2">
          <div className="flex h-28 w-full items-end justify-center gap-1">
            <div
              className="w-3 rounded-full bg-success"
              style={{ height: `${Math.max((d.income / max) * 100, d.income > 0 ? 4 : 0)}%` }}
              title={`Ingresos: ${d.income.toFixed(2)}`}
            />
            <div
              className="w-3 rounded-full bg-brand"
              style={{ height: `${Math.max((d.expense / max) * 100, d.expense > 0 ? 4 : 0)}%` }}
              title={`Gastos: ${d.expense.toFixed(2)}`}
            />
          </div>
          <span className="text-[10px] font-medium capitalize text-muted-soft">{formatShortMonth(d.month)}</span>
        </div>
      ))}
    </div>
  );
}
