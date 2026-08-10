export function formatMoney(amount: number | string, currency: string): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  return new Intl.NumberFormat("es-ES", { style: "currency", currency }).format(value);
}

export function formatDay(isoDate: string): string {
  return new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
    .format(new Date(isoDate))
    .toUpperCase();
}

export function dayKey(isoDate: string): string {
  return isoDate.slice(0, 10);
}

export function formatMonthLabel(monthKey: string): string {
  const [year, month] = monthKey.split("-").map(Number);
  return new Intl.DateTimeFormat("es-ES", { month: "long", year: "numeric" }).format(new Date(year, month - 1, 1));
}

export function formatShortMonth(monthKey: string): string {
  const [year, month] = monthKey.split("-").map(Number);
  return new Intl.DateTimeFormat("es-ES", { month: "short" }).format(new Date(year, month - 1, 1)).replace(".", "");
}

export function shiftMonth(monthKey: string, delta: number): { year: number; month: number } {
  const [year, month] = monthKey.split("-").map(Number);
  const date = new Date(year, month - 1 + delta, 1);
  return { year: date.getFullYear(), month: date.getMonth() + 1 };
}
