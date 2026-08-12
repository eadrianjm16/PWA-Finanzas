const PIN_KEY = "finanzas_pin_hash";
export const UNLOCK_KEY = "finanzas_unlocked";
const HIDDEN_AT_KEY = "finanzas_hidden_at";
export const RELOCK_AFTER_MS = 2 * 60 * 1000;

async function hashPin(pin: string): Promise<string> {
  const data = new TextEncoder().encode(pin);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function hasPinSet(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem(PIN_KEY);
}

export async function setPin(pin: string): Promise<void> {
  localStorage.setItem(PIN_KEY, await hashPin(pin));
  sessionStorage.setItem(UNLOCK_KEY, "1");
}

export function clearPin(): void {
  localStorage.removeItem(PIN_KEY);
  sessionStorage.removeItem(UNLOCK_KEY);
}

export async function verifyPin(pin: string): Promise<boolean> {
  const stored = localStorage.getItem(PIN_KEY);
  if (!stored) return true;
  return (await hashPin(pin)) === stored;
}

export function markHiddenNow(): void {
  sessionStorage.setItem(HIDDEN_AT_KEY, String(Date.now()));
}

export function shouldRelockAfterHidden(): boolean {
  const hiddenAt = Number(sessionStorage.getItem(HIDDEN_AT_KEY) || 0);
  return hiddenAt > 0 && Date.now() - hiddenAt > RELOCK_AFTER_MS;
}
