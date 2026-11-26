"use client";

import { useState, useEffect } from "react";
import { createPricingRule, PricingRuleFormState } from "@/actions/pricing";
import { Plus, X, Loader2 } from "lucide-react";
import { useActionState } from "react";
import { useTranslations } from "next-intl";
import PricingAdjustmentFields from "./PricingAdjustmentFields";

interface AddPricingRuleDialogProps {
    propertyId: string;
    basePrice: number;
}

const inputCls = "w-full px-3 py-2 rounded-lg bg-white/[0.06] border border-white/[0.10] text-white/90 focus:border-brand-primary/60 focus:ring-2 focus:ring-brand-primary/15 outline-none transition-all text-sm";
const labelCls = "block text-xs font-medium text-white/55 mb-1.5 uppercase tracking-wider";

export default function AddPricingRuleDialog({ propertyId, basePrice }: AddPricingRuleDialogProps) {
    const [isOpen, setIsOpen] = useState(false);
    const initialState: PricingRuleFormState = { error: "", success: false };
    const t = useTranslations("Common");
    const tProp = useTranslations("Properties");

    const createRuleWithId = createPricingRule.bind(null, propertyId);
    const [state, formAction, isPending] = useActionState(createRuleWithId, initialState);

    useEffect(() => {
        if (state.success && isOpen) {
            setIsOpen(false);
        }
    }, [state.success, isOpen]);

    return (
        <>
            <button
                onClick={() => setIsOpen(true)}
                className="inline-flex items-center px-4 py-2 bg-brand-primary hover:bg-brand-primary/80 text-white rounded-lg transition-colors text-sm font-medium"
            >
                <Plus size={15} className="mr-2" />
                {t('add')} {tProp('rules')}
            </button>

            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
                    <div className="glass-modal rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.08]">
                            <h3 className="text-base font-semibold text-white/90">{t('add')} {tProp('rules')}</h3>
                            <button
                                onClick={() => setIsOpen(false)}
                                className="text-white/40 hover:text-white/70 transition-colors"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <form action={formAction} className="p-6 space-y-4">
                            {state?.error && (
                                <div className="bg-brand-danger/10 border border-brand-danger/20 text-brand-danger/90 p-3 rounded-lg text-sm">
                                    {state.error}
                                </div>
                            )}

                            <div>
                                <label htmlFor="add_rule_name" className={labelCls}>
                                    {t('name')}
                                </label>
                                <input
                                    id="add_rule_name"
                                    name="name"
                                    type="text"
                                    required
                                    placeholder="High Season"
                                    className={inputCls}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="add_rule_start_date" className={labelCls}>{t('dateFrom')}</label>
                                    <input
                                        id="add_rule_start_date"
                                        name="start_date"
                                        type="date"
                                        required
                                        className={inputCls}
                                    />
                                </div>
                                <div>
                                    <label htmlFor="add_rule_end_date" className={labelCls}>{t('dateTo')}</label>
                                    <input
                                        id="add_rule_end_date"
                                        name="end_date"
                                        type="date"
                                        required
                                        className={inputCls}
                                    />
                                </div>
                            </div>

                            <PricingAdjustmentFields
                                idPrefix="add_rule"
                                basePrice={basePrice}
                                inputClassName={inputCls}
                                labelClassName={labelCls}
                            />

                            <div className="pt-2 flex justify-end space-x-3">
                                <button
                                    type="button"
                                    onClick={() => setIsOpen(false)}
                                    className="px-4 py-2 text-sm font-medium text-white/55 hover:bg-white/[0.05] hover:text-white/75 rounded-lg transition-colors"
                                >
                                    {t('cancel')}
                                </button>
                                <button
                                    type="submit"
                                    disabled={isPending}
                                    className="px-4 py-2 bg-brand-primary hover:bg-brand-primary/80 text-white rounded-lg disabled:opacity-60 flex items-center text-sm font-medium transition-colors"
                                >
                                    {isPending ? <Loader2 className="animate-spin mr-2" size={15} /> : null}
                                    {t('save')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </>
    );
}
