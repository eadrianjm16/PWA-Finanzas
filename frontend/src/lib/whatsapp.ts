// Contact Picker API: soportado hoy sobre todo en Chrome/Android para PWAs
// instaladas - no existe en iOS Safari ni en desktop, así que se usa como
// atajo opcional (feature-detected), nunca como la única forma de añadir
// el teléfono de alguien.
interface ContactsManager {
  select: (
    properties: string[],
    options: { multiple: boolean }
  ) => Promise<{ name?: string[]; tel?: string[] }[]>;
}

export function isContactPickerSupported(): boolean {
  return typeof navigator !== "undefined" && "contacts" in navigator && "ContactsManager" in window;
}

export async function pickPhoneContact(): Promise<{ name: string; phone: string } | null> {
  if (!isContactPickerSupported()) return null;
  try {
    const contactsApi = (navigator as unknown as { contacts: ContactsManager }).contacts;
    const [contact] = await contactsApi.select(["name", "tel"], { multiple: false });
    if (!contact) return null;
    return {
      name: contact.name?.[0]?.trim() ?? "",
      phone: contact.tel?.[0]?.trim() ?? "",
    };
  } catch {
    // El usuario canceló el selector, o el navegador lo bloqueó - no es un error real.
    return null;
  }
}

export function buildWhatsAppLink(phone: string, message: string): string {
  const digits = phone.replace(/[^0-9]/g, "");
  return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`;
}
