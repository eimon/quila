"use client";

import { useState, useEffect } from "react";
import { useTranslations, useLocale } from "next-intl";
import {
    TrendingUp,
    Wallet,
    Clock,
    Calendar,
    ChevronLeft,
    ChevronRight,
    Loader2,
    PieChart,
} from "lucide-react";
import { getFinancialSummary } from "@/actions/reports";
import { FinancialSummary } from "@/types/api";
import { formatPrice } from "@/lib/utils";

interface FinancialReportProps {
    propertyId: string;
}

export default function FinancialReport({ propertyId }: FinancialReportProps) {
    const [currentDate, setCurrentDate] = useState(new Date());
    // Keyed by request so loading is derived instead of set synchronously in the effect
    const [loaded, setLoaded] = useState<{ key: string; summary: FinancialSummary | null } | null>(null);

    const t = useTranslations("Reports");
    const tCommon = useTranslations("Common");
    const locale = useLocale();

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth() + 1;
    const requestKey = `${propertyId}:${year}-${month}`;

    useEffect(() => {
        let cancelled = false;
        getFinancialSummary(propertyId, year, month).then((data) => {
            if (!cancelled) setLoaded({ key: requestKey, summary: data });
        });
        return () => {
            cancelled = true;
        };
    }, [propertyId, year, month, requestKey]);

    const isLoading = loaded?.key !== requestKey;
    const summary = loaded && !isLoading ? loaded.summary : null;

    const prevMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
    };

    const nextMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
    };

    const formatMonth = () => {
        return new Intl.DateTimeFormat(locale, { month: 'long', year: 'numeric' }).format(currentDate);
    };

    const mainCards = summary ? [
        {
            title: t("income"),
            value: `$${formatPrice(summary.total_income)}`,
            icon: TrendingUp,
            color: "text-brand-success",
            bg: "bg-brand-success/10",
            detail: `${summary.total_bookings} ${t("totalBookings")}`
        },
        {
            title: t("paidIncome"),
            value: `$${formatPrice(summary.paid_income)}`,
            icon: Wallet,
            color: "text-brand-success",
            bg: "bg-brand-success/10",
            detail: t("paidIncomeDetail")
        },
        {
            title: t("pendingIncome"),
            value: `$${formatPrice(summary.pending_income)}`,
            icon: Clock,
            color: "text-brand-warning",
            bg: "bg-brand-warning/10",
            detail: t("pendingIncomeDetail")
        },
        {
            title: t("occupancy"),
            value: `${summary.occupancy_rate}%`,
            icon: Calendar,
            color: "text-brand-primary",
            bg: "bg-brand-primary/10",
            detail: `${summary.occupied_days}/${summary.days_in_month} ${t("occupiedDays")}`
        },
    ] : [];

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header & Month Selector */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-xl font-bold text-white/90">{t("title")}</h2>
                    <p className="text-white/45 mt-1 text-sm">{t("details")}</p>
                </div>

                <div className="inline-flex items-center glass rounded-xl p-1">
                    <button
                        onClick={prevMonth}
                        className="p-2 hover:bg-white/[0.06] rounded-lg transition-colors text-white/50 hover:text-white/80"
                    >
                        <ChevronLeft size={18} />
                    </button>
                    <span className="px-4 py-1 text-sm font-semibold text-white/75 min-w-[140px] text-center capitalize">
                        {formatMonth()}
                    </span>
                    <button
                        onClick={nextMonth}
                        className="p-2 hover:bg-white/[0.06] rounded-lg transition-colors text-white/50 hover:text-white/80"
                    >
                        <ChevronRight size={18} />
                    </button>
                </div>
            </div>

            {isLoading ? (
                <div className="flex flex-col items-center justify-center py-24 glass rounded-2xl gap-4">
                    <Loader2 className="animate-spin text-brand-primary/60" size={36} />
                    <p className="text-white/35 text-sm italic">{tCommon("loading")}</p>
                </div>
            ) : summary ? (
                <div className="space-y-8">
                    {/* Main Metric Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {mainCards.map((card) => (
                            <div key={card.title} className="glass rounded-2xl p-6 hover:bg-white/[0.07] transition-all group">
                                <div className="flex items-center justify-between mb-4">
                                    <div className={`p-2.5 rounded-xl ${card.bg} group-hover:scale-110 transition-transform`}>
                                        <card.icon className={card.color} size={20} />
                                    </div>
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-white/25 bg-white/[0.05] px-2 py-1 rounded-md">
                                        Real Data
                                    </span>
                                </div>
                                <p className="text-xs font-medium text-white/45 uppercase tracking-wider">{card.title}</p>
                                <p className="text-2xl font-bold text-white/90 mt-1">{card.value}</p>
                                <div className="mt-4 pt-4 border-t border-white/[0.06] flex items-center text-xs text-white/35">
                                    {card.detail}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-24 glass rounded-2xl border-dashed border border-white/[0.08] gap-2">
                    <PieChart size={40} className="text-white/15 mb-2" />
                    <p className="font-medium text-white/35">{t("noData")}</p>
                </div>
            )}
        </div>
    );
}
