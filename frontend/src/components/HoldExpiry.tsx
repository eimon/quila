"use client";

import { useLocale, useTranslations } from "next-intl";
import { Booking } from "@/types/api";
import { cn, holdExpiryState } from "@/lib/utils";

interface HoldExpiryProps {
    booking: Booking;
    className?: string;
}

/** "Vence <fecha>" for a live chatbot hold, "Vencido" once it expired; nothing otherwise. */
export default function HoldExpiry({ booking, className }: HoldExpiryProps) {
    const t = useTranslations("Bookings");
    const locale = useLocale();
    const state = holdExpiryState(booking);
    if (!state || !booking.expires_at) return null;

    if (state === "expired") {
        return (
            <span className={cn("text-[11px] font-medium text-brand-danger/80", className)}>
                {t("expired")}
            </span>
        );
    }

    const date = new Date(booking.expires_at).toLocaleString(locale, {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
    return (
        <span className={cn("text-[11px] text-brand-warning/80", className)}>
            {t("expiresAt", { date })}
        </span>
    );
}
