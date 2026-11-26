"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { PricingAdjustmentType } from "@/types/api";
import { formatPrice } from "@/lib/utils";

interface PricingAdjustmentFieldsProps {
    idPrefix: string;
    basePrice: number;
    defaultType?: PricingAdjustmentType;
    defaultValue?: number;
    defaultPriority?: number;
    inputClassName: string;
    labelClassName: string;
}

/** Nightly price a rule produces over the given base price (mirrors the API formula). */
export function adjustedPrice(basePrice: number, type: PricingAdjustmentType, value: number): number {
    return type === PricingAdjustmentType.FIXED_PRICE ? value : basePrice * (1 + value / 100);
}

/**
 * Adjustment type, value and priority inputs shared by every pricing rule form.
 * Field names match the API: adjustment_type, adjustment_value, priority.
 */
export default function PricingAdjustmentFields({
    idPrefix,
    basePrice,
    defaultType = PricingAdjustmentType.PERCENTAGE,
    defaultValue = 0,
    defaultPriority = 0,
    inputClassName,
    labelClassName,
}: PricingAdjustmentFieldsProps) {
    const t = useTranslations("PricingRules");
    const tEnums = useTranslations("Enums.PricingAdjustmentType");
    const [type, setType] = useState<PricingAdjustmentType>(defaultType);
    const [value, setValue] = useState(String(defaultValue));

    const isPercentage = type === PricingAdjustmentType.PERCENTAGE;
    const numericValue = parseFloat(value);
    const estimatedPrice = Number.isFinite(numericValue) ? adjustedPrice(basePrice, type, numericValue) : null;

    return (
        <>
            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label htmlFor={`${idPrefix}_adjustment_type`} className={labelClassName}>
                        {t("adjustmentType")}
                    </label>
                    <select
                        id={`${idPrefix}_adjustment_type`}
                        name="adjustment_type"
                        value={type}
                        onChange={(e) => setType(e.target.value as PricingAdjustmentType)}
                        className={inputClassName}
                    >
                        {Object.values(PricingAdjustmentType).map((option) => (
                            <option key={option} value={option}>
                                {tEnums(option)}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <label htmlFor={`${idPrefix}_priority`} className={labelClassName}>
                        {t("priority")}
                    </label>
                    <input
                        id={`${idPrefix}_priority`}
                        name="priority"
                        type="number"
                        step="1"
                        defaultValue={defaultPriority}
                        className={inputClassName}
                    />
                </div>
            </div>
            <p className="text-xs text-white/30 -mt-2">{t("priorityHint")}</p>

            <div>
                <div className="flex items-center justify-between mb-1.5">
                    <label htmlFor={`${idPrefix}_adjustment_value`} className={labelClassName}>
                        {isPercentage ? t("percentageValue") : t("fixedPriceValue")}
                    </label>
                    {estimatedPrice !== null && (
                        <span className="text-xs font-semibold text-brand-primary/80">
                            {t("estimatedPrice", { price: formatPrice(estimatedPrice) })}
                        </span>
                    )}
                </div>
                <input
                    id={`${idPrefix}_adjustment_value`}
                    name="adjustment_value"
                    type="number"
                    step="0.01"
                    min={isPercentage ? "-99.99" : "0.01"}
                    required
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    className={inputClassName}
                />
                <p className="text-xs text-white/30 mt-1">
                    {isPercentage
                        ? t("percentageHint", { price: formatPrice(basePrice) })
                        : t("fixedPriceHint")}
                </p>
            </div>
        </>
    );
}
