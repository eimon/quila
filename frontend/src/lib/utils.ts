import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export function formatPrice(value: number | string): string {
    return Math.round(Number(value)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

export function formatPriceCompact(value: number | string): string {
    const n = Math.round(Number(value));
    if (n >= 1_000_000) return `${Math.round(n / 100_000) / 10}M`;
    if (n >= 1_000) return `${Math.round(n / 100) / 10}k`;
    return n.toString();
}

export type HoldExpiryState = "active" | "expired";

/**
 * Expiry state of a chatbot hold: "active" while a TENTATIVE hold has not expired,
 * "expired" once expires_at is past and the hold was not converted (CANCELLED, or
 * TENTATIVE not swept yet). null when the booking is not an expiring hold.
 */
export function holdExpiryState(
    booking: { status: string; expires_at?: string | null },
    now: number = Date.now()
): HoldExpiryState | null {
    if (!booking.expires_at) return null;
    const expired = new Date(booking.expires_at).getTime() <= now;
    if (booking.status === "TENTATIVE") return expired ? "expired" : "active";
    if (booking.status === "CANCELLED" && expired) return "expired";
    return null;
}
