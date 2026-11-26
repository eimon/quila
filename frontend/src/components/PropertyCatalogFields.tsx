"use client";

import { useTranslations } from "next-intl";
import { Property } from "@/types/api";

interface PropertyCatalogFieldsProps {
    property?: Property;
    inputCls: string;
    labelCls: string;
}

// "14:00:00" -> "14:00" for <input type="time">
function toTimeInput(value?: string | null): string {
    return value ? value.slice(0, 5) : "";
}

export default function PropertyCatalogFields({ property, inputCls, labelCls }: PropertyCatalogFieldsProps) {
    const t = useTranslations("Properties.create");
    const tCommon = useTranslations("Common");
    const optional = (
        <span className="text-white/25 normal-case tracking-normal">({tCommon("optional")})</span>
    );

    return (
        <div className="space-y-4 pt-4 border-t border-white/[0.07]">
            <div>
                <h4 className="text-sm font-semibold text-white/80">{t("catalogSection")}</h4>
                <p className="text-xs text-white/35 mt-0.5">{t("catalogHint")}</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                    <label htmlFor="max_guests" className={labelCls}>{t("maxGuests")} {optional}</label>
                    <input
                        id="max_guests"
                        name="max_guests"
                        type="number"
                        min="1"
                        step="1"
                        defaultValue={property?.max_guests ?? ""}
                        className={inputCls}
                    />
                </div>
                <div>
                    <label htmlFor="check_in_time" className={labelCls}>{t("checkInTime")} {optional}</label>
                    <input
                        id="check_in_time"
                        name="check_in_time"
                        type="time"
                        defaultValue={toTimeInput(property?.check_in_time)}
                        className={inputCls}
                    />
                </div>
                <div>
                    <label htmlFor="check_out_time" className={labelCls}>{t("checkOutTime")} {optional}</label>
                    <input
                        id="check_out_time"
                        name="check_out_time"
                        type="time"
                        defaultValue={toTimeInput(property?.check_out_time)}
                        className={inputCls}
                    />
                </div>
            </div>

            <div>
                <label htmlFor="amenities" className={labelCls}>{t("amenities")} {optional}</label>
                <textarea
                    id="amenities"
                    name="amenities"
                    rows={3}
                    defaultValue={(property?.amenities ?? []).join("\n")}
                    placeholder={t("amenitiesPlaceholder")}
                    className={`${inputCls} resize-y`}
                />
                <p className="text-xs text-white/25 mt-1">{t("amenitiesHint")}</p>
            </div>

            <div>
                <label htmlFor="cancellation_policy" className={labelCls}>{t("cancellationPolicy")} {optional}</label>
                <textarea
                    id="cancellation_policy"
                    name="cancellation_policy"
                    rows={3}
                    defaultValue={property?.cancellation_policy ?? ""}
                    className={`${inputCls} resize-y`}
                />
            </div>

            <div>
                <label htmlFor="house_rules" className={labelCls}>{t("houseRules")} {optional}</label>
                <textarea
                    id="house_rules"
                    name="house_rules"
                    rows={3}
                    defaultValue={property?.house_rules ?? ""}
                    className={`${inputCls} resize-y`}
                />
            </div>
        </div>
    );
}
