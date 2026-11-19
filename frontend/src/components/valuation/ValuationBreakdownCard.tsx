"use client";

import React from "react";
import { AlertCircle, Calculator, Cpu, FileSpreadsheet, FlaskConical, Scale } from "lucide-react";
import { formatGrams, formatINR } from "@/lib/i18n";
import { CalculationStep, DeductionItem } from "@/lib/types";
import { Badge, Card } from "@/components/ui/primitives";

export function ValuationBreakdownCard({
  measurement,
  rate,
  deductions,
  valuation,
  title = "Transparent Valuation Breakdown",
}: {
  measurement: {
    gross_weight_g: string;
    non_gold_weight_g: string;
    net_gold_weight_g: string;
    purity_pct: string;
    purity_karat_label?: string;
    measurement_source: string;
    instrument_name?: string | null;
    test_report_ref?: string | null;
  };
  rate: {
    rate_24k_per_g: string;
    rate_source: string;
    is_simulated_rate?: boolean;
  };
  deductions: DeductionItem[];
  valuation: {
    pure_gold_weight_g: string;
    gross_reference_value_inr: string;
    total_deductions_inr: string;
    calculated_net_value_inr: string;
    jeweller_offered_value_inr: string;
    offer_difference_inr: string;
    offer_difference_explanation?: string | null;
    calculation_steps?: CalculationStep[];
  };
  title?: string;
}) {
  const sourceBadge =
    measurement.measurement_source === "instrument" ? (
      <Badge tone="emerald">
        <Cpu className="h-3 w-3" />
        Instrument Reading {measurement.test_report_ref ? `(${measurement.test_report_ref})` : ""}
      </Badge>
    ) : measurement.measurement_source === "simulated_demo" ? (
      <Badge tone="amber">
        <FlaskConical className="h-3 w-3" />
        Simulated Demo Measurement (Illustrative)
      </Badge>
    ) : (
      <Badge tone="sky">
        <FileSpreadsheet className="h-3 w-3" />
        Manually Entered Reading
      </Badge>
    );

  const grossValNum = Number(valuation.gross_reference_value_inr || 0);
  const netOfferNum = Number(valuation.jeweller_offered_value_inr || 0);
  const retainedPct =
    grossValNum > 0 ? Math.max(0, Math.min(100, (netOfferNum / grossValNum) * 100)) : 100;
  const deductedPct = Math.max(0, 100 - retainedPct);
  const offerDiff = Number(valuation.offer_difference_inr || 0);

  return (
    <Card className="space-y-5 print-card">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <Calculator className="h-4 w-4 text-[#D4AF37]" />
          <h2 className="text-base font-semibold text-[#F5F5F7]">{title}</h2>
        </div>
        {sourceBadge}
      </div>

      {/* Key Measurement & Rate Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-3">
          <p className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">Gross Weight</p>
          <p className="mt-1 text-base font-semibold tabular-nums text-[#F5F5F7]">
            {formatGrams(measurement.gross_weight_g)}
          </p>
          <p className="text-[11px] text-[#6E6E7A] tabular-nums">
            Non-gold: {formatGrams(measurement.non_gold_weight_g)}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-3">
          <p className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">Net Gold Weight</p>
          <p className="mt-1 text-base font-semibold tabular-nums text-[#F5F5F7]">
            {formatGrams(measurement.net_gold_weight_g)}
          </p>
          <p className="text-[11px] text-[#6E6E7A]">
            Purity: {measurement.purity_pct}% {measurement.purity_karat_label || ""}
          </p>
        </div>
        <div className="rounded-xl border border-[#D4AF37]/30 bg-[#D4AF37]/10 p-3">
          <p className="text-[11px] uppercase tracking-wider text-[#E8D5B5]">24K Pure Equivalent</p>
          <p className="mt-1 text-base font-semibold tabular-nums text-[#D4AF37]">
            {formatGrams(valuation.pure_gold_weight_g)}
          </p>
          <p className="text-[11px] text-[#9A9AA6]">Net × Purity / 100</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-3">
          <p className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">24K Gold Rate</p>
          <p className="mt-1 text-base font-semibold tabular-nums text-[#F5F5F7]">
            {formatINR(rate.rate_24k_per_g)}/g
          </p>
          <p className="text-[11px] text-[#6E6E7A] truncate" title={rate.rate_source}>
            {rate.rate_source}
          </p>
        </div>
      </div>

      {/* Swiss-Ledger Equation & Retention Bar */}
      <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/65 p-3.5 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[#9A9AA6]">
          <span className="font-mono tabular-nums text-[#E8D5B5]">
            {Number(measurement.net_gold_weight_g).toFixed(3)}g × {measurement.purity_pct}% ={" "}
            {Number(valuation.pure_gold_weight_g).toFixed(4)}g × {formatINR(rate.rate_24k_per_g)}
          </span>
          <span className="font-semibold text-[#F5F5F7] tabular-nums">
            {retainedPct.toFixed(1)}% retained by customer
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.06] flex">
          <div
            className="h-full bg-gradient-to-r from-[#D4AF37] to-[#E8D5B5] transition-all duration-300"
            style={{ width: `${retainedPct}%` }}
          />
          {deductedPct > 0.1 && (
            <div
              className="h-full bg-rose-400/70 transition-all duration-300"
              style={{ width: `${deductedPct}%` }}
            />
          )}
        </div>
      </div>

      {/* Step-by-step Formula Breakdown */}
      <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/60 p-4 space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-[#9A9AA6] flex items-center gap-1.5">
            <Scale className="h-3.5 w-3.5 text-[#D4AF37]" />
            Gross Reference Value ({Number(valuation.pure_gold_weight_g).toFixed(4)} g × {formatINR(rate.rate_24k_per_g)})
          </span>
          <span className="font-semibold tabular-nums text-[#F5F5F7]">
            {formatINR(valuation.gross_reference_value_inr)}
          </span>
        </div>

        {/* Itemized Deductions */}
        <div className="border-t border-white/8 pt-3 space-y-2">
          <div className="flex items-center justify-between text-xs uppercase tracking-wider text-[#9A9AA6]">
            <span>Itemized Deductions</span>
            <span className="tabular-nums text-rose-300">- {formatINR(valuation.total_deductions_inr)}</span>
          </div>

          {deductions.length === 0 ? (
            <p className="text-xs text-[#6E6E7A]">No deductions recorded.</p>
          ) : (
            <div className="space-y-2">
              {deductions.map((d, idx) => {
                const hasReason = Boolean(d.reason && d.reason.trim().length >= 8);
                return (
                  <div
                    key={d.id || `${d.label}-${idx}`}
                    className={`rounded-xl border px-3.5 py-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5 ${
                      hasReason
                        ? "border-white/10 bg-[#141418]"
                        : "border-amber-500/40 bg-amber-500/[0.07]"
                    }`}
                  >
                    <div className="space-y-0.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-[#F5F5F7]">{d.label}</span>
                        <span className="text-[10px] uppercase tracking-wider text-[#6E6E7A]">
                          {d.deduction_type}
                        </span>
                        {!hasReason && (
                          <Badge tone="amber" className="py-0 text-[10px]">
                            <AlertCircle className="h-2.5 w-2.5" />
                            Explanation Needed
                          </Badge>
                        )}
                      </div>
                      <p className={`text-xs ${hasReason ? "text-[#9A9AA6]" : "text-amber-200"}`}>
                        {hasReason ? d.reason : "No written explanation documented for this deduction."}
                      </p>
                    </div>
                    <div className="sm:text-right shrink-0">
                      <span className="text-sm font-semibold tabular-nums text-rose-200">
                        - {formatINR(d.amount_inr)}
                      </span>
                      {d.percentage_of_gross && (
                        <p className="text-[11px] text-[#6E6E7A] tabular-nums">{d.percentage_of_gross}%</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Final Calculated vs Offered */}
        <div className="border-t border-white/10 pt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-xl border border-white/10 bg-[#141418] p-3.5">
            <p className="text-xs text-[#9A9AA6]">Calculated Net Value</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-[#F5F5F7]">
              {formatINR(valuation.calculated_net_value_inr)}
            </p>
          </div>
          <div className="rounded-xl border border-[#D4AF37]/40 bg-[#D4AF37]/12 p-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
            <p className="text-xs text-[#E8D5B5]">Jeweller Offered Value</p>
            <p className="mt-1 text-xl font-bold tabular-nums text-[#D4AF37]">
              {formatINR(valuation.jeweller_offered_value_inr)}
            </p>
          </div>
        </div>

        {Math.abs(offerDiff) > 0.01 && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-xs text-amber-200">
            <span className="font-semibold">
              Offer Variance ({offerDiff > 0 ? "+" : ""}
              {formatINR(offerDiff)}):{" "}
            </span>
            {valuation.offer_difference_explanation ||
              "No explanation documented for the difference between calculated value and offered value."}
          </div>
        )}
      </div>

      {measurement.instrument_name && (
        <p className="text-xs text-[#9A9AA6]">
          Assay Reference: <span className="text-[#F5F5F7]">{measurement.instrument_name}</span>
          {measurement.test_report_ref ? ` · Report #${measurement.test_report_ref}` : ""}
        </p>
      )}
    </Card>
  );
}
