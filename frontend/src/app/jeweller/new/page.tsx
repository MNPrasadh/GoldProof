"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Calculator,
  CloudOff,
  Cpu,
  FileSpreadsheet,
  FlaskConical,
  Plus,
  ScanLine,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatGrams, formatINR } from "@/lib/i18n";
import { enqueueOfflineDraft } from "@/lib/offline-store";
import { ValuationPreviewResponse } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, FieldLabel, Input, Select, Textarea } from "@/components/ui/primitives";
import { ValuationBreakdownCard } from "@/components/valuation/ValuationBreakdownCard";
import { IntelligenceFlagsCard } from "@/components/valuation/IntelligenceFlagsCard";

interface DeductionFormRow {
  deduction_type: string;
  label: string;
  amount_inr: string;
  reason: string;
  supporting_doc_ref: string;
}

const PURITY_PRESETS = [
  { karat: "24K (995)", pct: "99.50", label: "24K · 99.5%" },
  { karat: "22K (916)", pct: "91.60", label: "22K · 91.6%" },
  { karat: "18K (750)", pct: "75.00", label: "18K · 75.0%" },
  { karat: "14K (585)", pct: "58.50", label: "14K · 58.5%" },
];

export default function NewGoldExchangePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [customerName, setCustomerName] = useState("Lakshmi Narayanan");
  const [customerMobile, setCustomerMobile] = useState("+919840122334");
  const [customerLang, setCustomerLang] = useState<"en" | "ta">("ta");
  const [consentGranted, setConsentGranted] = useState(false);

  const [itemDescription, setItemDescription] = useState("22K Gold Necklace");
  const [category, setCategory] = useState("necklace");
  const [hallmarkHuid, setHallmarkHuid] = useState("");
  const [stoneDesc, setStoneDesc] = useState("");

  const [grossWeight, setGrossWeight] = useState("20.00");
  const [nonGoldWeight, setNonGoldWeight] = useState("0.00");
  const [purityPct, setPurityPct] = useState("91.60");
  const [karatLabel, setKaratLabel] = useState("22K (916)");
  const [measurementSource, setMeasurementSource] = useState<"instrument" | "manual" | "simulated_demo">(
    "simulated_demo"
  );
  const [instrumentName, setInstrumentName] = useState("Simulated XRF Benchtop Demo");
  const [testReportRef, setTestReportRef] = useState("DEMO-XRF-101");
  const [ocrExtracted, setOcrExtracted] = useState(false);

  const [rate24k, setRate24k] = useState("7600.00");
  const [rateSource, setRateSource] = useState("Illustrative 24K Reference Rate [DEMO]");
  const [benchmarkRate, setBenchmarkRate] = useState("7600.00");
  const [isDemo, setIsDemo] = useState(true);

  const [deductions, setDeductions] = useState<DeductionFormRow[]>([
    {
      deduction_type: "melting_refining",
      label: "Melting & Refining Charge",
      amount_inr: "3000.00",
      reason: "Standard crucible melting and assay documentation fee per shop tariff.",
      supporting_doc_ref: "POL-2026",
    },
  ]);

  const [offeredValue, setOfferedValue] = useState("");
  const [offerDiffExplanation, setOfferDiffExplanation] = useState("");
  const [notes, setNotes] = useState("");

  const [preview, setPreview] = useState<ValuationPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offlineSavedMsg, setOfflineSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "jeweller")) {
      router.push("/");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = sessionStorage.getItem("goldproof_ocr_prefill");
    if (!raw) return;
    try {
      const data = JSON.parse(raw);
      if (data.item_description) setItemDescription(data.item_description);
      if (data.gross_weight_g) setGrossWeight(data.gross_weight_g);
      if (data.non_gold_weight_g) setNonGoldWeight(data.non_gold_weight_g);
      if (data.purity_pct) setPurityPct(data.purity_pct);
      if (data.rate_24k_per_g) setRate24k(data.rate_24k_per_g);
      if (data.test_report_ref) setTestReportRef(data.test_report_ref);
      if (data.instrument_name) setInstrumentName(data.instrument_name);
      setMeasurementSource("manual");
      setOcrExtracted(true);
      sessionStorage.removeItem("goldproof_ocr_prefill");
    } catch {
      // ignore invalid prefill
    }
  }, []);

  const netNum = Math.max(0, Number(grossWeight || 0) - Number(nonGoldWeight || 0));
  const netWeightDerived = netNum.toFixed(4);
  const livePureGold = netNum * (Number(purityPct || 0) / 100);
  const liveGrossInr = livePureGold * Number(rate24k || 0);
  const liveDeductionsInr = deductions.reduce((acc, d) => acc + Math.max(0, Number(d.amount_inr || 0)), 0);
  const liveNetInr = Math.max(0, liveGrossInr - liveDeductionsInr);

  const runPreview = async () => {
    setError(null);
    setPreviewLoading(true);
    try {
      const res = await apiRequest<ValuationPreviewResponse>("/api/transactions/preview-valuation", {
        method: "POST",
        body: JSON.stringify({
          gross_weight_g: grossWeight || "0",
          non_gold_weight_g: nonGoldWeight || "0",
          net_gold_weight_g: netWeightDerived,
          purity_pct: purityPct || "0",
          measurement_source: measurementSource,
          instrument_name: instrumentName || null,
          test_report_ref: testReportRef || null,
          rate_24k_per_g: rate24k || "0",
          rate_source: rateSource || "Shop Board",
          benchmark_reference_rate_per_g: benchmarkRate || null,
          deductions: deductions.map((d) => ({
            deduction_type: d.deduction_type,
            label: d.label || "Deduction",
            amount_inr: d.amount_inr || "0",
            reason: d.reason,
            supporting_doc_ref: d.supporting_doc_ref || null,
          })),
          jeweller_offered_value_inr: offeredValue ? offeredValue : null,
          offer_difference_explanation: offerDiffExplanation || null,
          is_demo: isDemo,
        }),
      });
      setPreview(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not calculate preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const buildSubmissionPayload = () => ({
    customer_name: customerName,
    customer_mobile: customerMobile,
    customer_preferred_language: customerLang,
    consent_granted: consentGranted,
    item_description: itemDescription,
    category,
    hallmark_huid: hallmarkHuid || null,
    stone_or_non_gold_description: stoneDesc || null,
    gross_weight_g: grossWeight,
    non_gold_weight_g: nonGoldWeight || "0",
    net_gold_weight_g: netWeightDerived,
    purity_pct: purityPct,
    purity_karat_label: karatLabel,
    measurement_source: measurementSource,
    instrument_name: instrumentName || null,
    test_report_ref: testReportRef || null,
    ocr_extracted: ocrExtracted,
    rate_24k_per_g: rate24k,
    rate_source: rateSource,
    benchmark_reference_rate_per_g: benchmarkRate || null,
    is_simulated_rate: isDemo || measurementSource === "simulated_demo",
    deductions: deductions.map((d) => ({
      deduction_type: d.deduction_type,
      label: d.label,
      amount_inr: d.amount_inr || "0",
      reason: d.reason,
      supporting_doc_ref: d.supporting_doc_ref || null,
    })),
    jeweller_offered_value_inr: offeredValue ? offeredValue : null,
    offer_difference_explanation: offerDiffExplanation || null,
    notes: notes || null,
    is_demo: isDemo,
  });

  const handleSubmitOnline = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setOfflineSavedMsg(null);
    if (!consentGranted) {
      setError("Explicit customer consent must be confirmed before recording this transaction.");
      return;
    }

    const payload = buildSubmissionPayload();
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      const draft = enqueueOfflineDraft(payload);
      setOfflineSavedMsg(`Device is offline. Saved locally as ${draft.client_draft_id}. Sync when reconnected.`);
      return;
    }

    setSubmitting(true);
    try {
      const created = await apiRequest<{ id: string }>("/api/transactions", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.push(`/jeweller/transactions/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save transaction.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSaveOfflineDraft = () => {
    setError(null);
    if (!consentGranted) {
      setError("Confirm customer consent before saving an offline draft.");
      return;
    }
    const draft = enqueueOfflineDraft(buildSubmissionPayload());
    setOfflineSavedMsg(
      `Saved offline draft ${draft.client_draft_id}. Remember: offline drafts are NOT signed or verified until synced.`
    );
  };

  return (
    <AppShell
      title="New Gold Exchange"
      subtitle="Document measurements, purity provenance, 24K reference rate, and itemized deductions transparently."
    >
      <form onSubmit={handleSubmitOnline} className="space-y-6">
        {/* Sticky Live Calculation Ribbon */}
        <div className="sticky top-[62px] z-20 rounded-2xl border border-[#D4AF37]/30 bg-[#121216]/92 backdrop-blur-xl p-3.5 shadow-[0_12px_30px_rgba(0,0,0,0.65)]">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#9A9AA6]">24K Pure Gold</p>
              <p className="font-semibold tabular-nums text-[#E8D5B5] text-sm">{formatGrams(livePureGold)}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#9A9AA6]">Gross Value</p>
              <p className="font-semibold tabular-nums text-[#F5F5F7] text-sm">{formatINR(liveGrossInr)}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#9A9AA6]">Deductions</p>
              <p className="font-semibold tabular-nums text-rose-300 text-sm">- {formatINR(liveDeductionsInr)}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]">Calculated Net</p>
              <p className="font-bold tabular-nums text-[#D4AF37] text-base">{formatINR(liveNetInr)}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {ocrExtracted && <Badge tone="sky">Prefilled from Human-Confirmed OCR</Badge>}
            <label className="inline-flex items-center gap-2 text-xs text-[#E8D5B5] cursor-pointer">
              <input
                type="checkbox"
                checked={isDemo}
                onChange={(e) => setIsDemo(e.target.checked)}
                className="h-4 w-4 accent-[#D4AF37]"
              />
              Mark as Demo / Practice Record
            </label>
          </div>

          <Button type="button" variant="secondary" size="sm" onClick={() => router.push("/jeweller/ocr")}>
            <ScanLine className="h-4 w-4 text-[#D4AF37]" />
            Import from Paper Receipt / Assay OCR
          </Button>
        </div>

        {/* 1. Customer & Consent */}
        <Card className="space-y-4">
          <h2 className="text-base font-semibold text-[#F5F5F7] border-b border-white/10 pb-2">
            1. Customer Details &amp; Explicit Consent
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <FieldLabel required>Customer Name</FieldLabel>
              <Input value={customerName} onChange={(e) => setCustomerName(e.target.value)} required />
            </div>
            <div>
              <FieldLabel required>Mobile Number</FieldLabel>
              <Input value={customerMobile} onChange={(e) => setCustomerMobile(e.target.value)} required />
            </div>
            <div>
              <FieldLabel>Preferred Language</FieldLabel>
              <Select
                value={customerLang}
                onChange={(e) => setCustomerLang(e.target.value as "en" | "ta")}
              >
                <option value="ta">தமிழ் (Tamil)</option>
                <option value="en">English</option>
              </Select>
            </div>
          </div>

          <label className="flex items-start gap-3 rounded-xl border border-[#D4AF37]/30 bg-[#D4AF37]/8 p-3.5 text-xs text-[#E8D5B5] cursor-pointer">
            <input
              type="checkbox"
              checked={consentGranted}
              onChange={(e) => setConsentGranted(e.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 accent-[#D4AF37]"
            />
            <span>
              <strong>Explicit Customer Consent:</strong> The customer has seen the weighing &amp; purity reading
              process and consents to recording this gold exchange valuation and Digital Gold Passport in
              GoldProof.
            </span>
          </label>
        </Card>

        {/* 2. Jewellery & Measurement Provenance */}
        <Card className="space-y-4">
          <h2 className="text-base font-semibold text-[#F5F5F7] border-b border-white/10 pb-2">
            2. Gold Item &amp; Measurement Provenance
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="sm:col-span-2">
              <FieldLabel required>Jewellery Description</FieldLabel>
              <Input value={itemDescription} onChange={(e) => setItemDescription(e.target.value)} required />
            </div>
            <div>
              <FieldLabel>Category</FieldLabel>
              <Select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="necklace">Necklace / Haram</option>
                <option value="bangle">Bangle / Bracelet</option>
                <option value="ring">Ring</option>
                <option value="chain">Chain</option>
                <option value="coin">Coin / Bar</option>
                <option value="earring">Earrings</option>
                <option value="ornament">Other Ornament</option>
              </Select>
            </div>
            <div>
              <FieldLabel>Hallmark HUID (Optional)</FieldLabel>
              <Input value={hallmarkHuid} onChange={(e) => setHallmarkHuid(e.target.value)} placeholder="e.g. AB12CD" />
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <FieldLabel required hint="grams">Gross Weight</FieldLabel>
              <Input
                type="number"
                step="0.001"
                value={grossWeight}
                onChange={(e) => setGrossWeight(e.target.value)}
                required
              />
            </div>
            <div>
              <FieldLabel hint="stones/wax">Non-Gold Weight</FieldLabel>
              <Input
                type="number"
                step="0.001"
                value={nonGoldWeight}
                onChange={(e) => setNonGoldWeight(e.target.value)}
              />
            </div>
            <div>
              <FieldLabel hint="derived">Net Gold Weight</FieldLabel>
              <Input value={netWeightDerived} readOnly className="bg-white/5 text-[#E8D5B5] tabular-nums" />
            </div>
            <div>
              <FieldLabel required hint="%">Purity</FieldLabel>
              <Input
                type="number"
                step="0.01"
                value={purityPct}
                onChange={(e) => setPurityPct(e.target.value)}
                required
              />
            </div>
          </div>

          {/* 1-Tap Purity Presets */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">Quick Purity:</span>
            {PURITY_PRESETS.map((preset) => (
              <button
                key={preset.karat}
                type="button"
                onClick={() => {
                  setPurityPct(preset.pct);
                  setKaratLabel(preset.karat);
                }}
                className={`min-h-[34px] rounded-full border px-3 text-xs font-medium cursor-pointer transition-colors ${
                  purityPct === preset.pct
                    ? "border-[#D4AF37] bg-[#D4AF37]/20 text-[#E8D5B5]"
                    : "border-white/12 bg-white/[0.04] text-[#9A9AA6] hover:text-white"
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>

          {/* 3 Tactile Measurement Source Cards */}
          <div>
            <FieldLabel required>Measurement Provenance (Honesty Declaration)</FieldLabel>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                {
                  value: "instrument" as const,
                  title: "Instrument Reading",
                  desc: "Live XRF / Karatometer assay machine with report ID",
                  icon: Cpu,
                },
                {
                  value: "manual" as const,
                  title: "Manual Entry",
                  desc: "Touchstone / counter scale measurement entered by staff",
                  icon: FileSpreadsheet,
                },
                {
                  value: "simulated_demo" as const,
                  title: "Simulated Demo",
                  desc: "Illustrative demo values — never treated as real assay",
                  icon: FlaskConical,
                },
              ].map((opt) => {
                const Icon = opt.icon;
                const active = measurementSource === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setMeasurementSource(opt.value)}
                    className={`text-left rounded-xl border p-3.5 transition-all cursor-pointer ${
                      active
                        ? "border-[#D4AF37] bg-[#D4AF37]/12 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]"
                        : "border-white/10 bg-[#0B0B0D]/70 hover:border-white/25"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon className={`h-4 w-4 ${active ? "text-[#D4AF37]" : "text-[#9A9AA6]"}`} />
                      <span className="text-xs font-semibold text-[#F5F5F7]">{opt.title}</span>
                    </div>
                    <p className="mt-1 text-[11px] text-[#9A9AA6] leading-snug">{opt.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <FieldLabel>Karat Label</FieldLabel>
              <Input value={karatLabel} onChange={(e) => setKaratLabel(e.target.value)} />
            </div>
            <div>
              <FieldLabel>Instrument Name</FieldLabel>
              <Input
                value={instrumentName}
                onChange={(e) => setInstrumentName(e.target.value)}
                placeholder="e.g. SpectroXRF M4"
              />
            </div>
            <div>
              <FieldLabel>Test Report Ref</FieldLabel>
              <Input
                value={testReportRef}
                onChange={(e) => setTestReportRef(e.target.value)}
                placeholder="e.g. XRF-2026-109"
              />
            </div>
          </div>

          {measurementSource === "simulated_demo" && (
            <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2 text-xs text-amber-200">
              Labelled as <strong>Simulated Demo Measurement</strong>. GoldProof never represents simulated readings as real instrument evidence.
            </p>
          )}

          <div>
            <FieldLabel>Stone / Non-Gold Notes (Optional)</FieldLabel>
            <Input
              value={stoneDesc}
              onChange={(e) => setStoneDesc(e.target.value)}
              placeholder="e.g. Synthetic ruby stones detached before final weighing"
            />
          </div>
        </Card>

        {/* 3. Rate & Itemized Deductions */}
        <Card className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <h2 className="text-base font-semibold text-[#F5F5F7]">3. Reference Rate &amp; Itemized Deductions</h2>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() =>
                setDeductions((prev) => [
                  ...prev,
                  {
                    deduction_type: "other",
                    label: "Additional Charge",
                    amount_inr: "0.00",
                    reason: "",
                    supporting_doc_ref: "",
                  },
                ])
              }
            >
              <Plus className="h-4 w-4" />
              Add Deduction
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <FieldLabel required hint="INR / gram">24K Reference Rate</FieldLabel>
              <Input type="number" step="0.01" value={rate24k} onChange={(e) => setRate24k(e.target.value)} required />
            </div>
            <div>
              <FieldLabel required>Rate Source</FieldLabel>
              <Input value={rateSource} onChange={(e) => setRateSource(e.target.value)} required />
            </div>
            <div>
              <FieldLabel hint="for consistency check">Benchmark 24K Rate</FieldLabel>
              <Input
                type="number"
                step="0.01"
                value={benchmarkRate}
                onChange={(e) => setBenchmarkRate(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-3">
            {deductions.map((row, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-white/10 bg-[#0B0B0D]/70 p-3.5 space-y-3"
              >
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                  <div>
                    <FieldLabel>Type</FieldLabel>
                    <Select
                      value={row.deduction_type}
                      onChange={(e) =>
                        setDeductions((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, deduction_type: e.target.value } : r))
                        )
                      }
                    >
                      <option value="melting_refining">Melting &amp; Refining</option>
                      <option value="assay_testing">Assay / Testing Fee</option>
                      <option value="stone_removal">Stone Removal</option>
                      <option value="wastage_adjustment">Wastage Adjustment</option>
                      <option value="other">Other</option>
                    </Select>
                  </div>
                  <div className="sm:col-span-2">
                    <FieldLabel>Deduction Label</FieldLabel>
                    <Input
                      value={row.label}
                      onChange={(e) =>
                        setDeductions((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, label: e.target.value } : r))
                        )
                      }
                      required
                    />
                  </div>
                  <div className="flex gap-2 items-end">
                    <div className="flex-1">
                      <FieldLabel>Amount (INR)</FieldLabel>
                      <Input
                        type="number"
                        step="0.01"
                        value={row.amount_inr}
                        onChange={(e) =>
                          setDeductions((prev) =>
                            prev.map((r, i) => (i === idx ? { ...r, amount_inr: e.target.value } : r))
                          )
                        }
                        required
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => setDeductions((prev) => prev.filter((_, i) => i !== idx))}
                      className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl border border-white/10 text-rose-300 hover:bg-rose-500/15 cursor-pointer"
                      title="Remove deduction"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div>
                  <FieldLabel hint="required to avoid unexplained deduction warning">
                    Written Reason Shown to Customer
                  </FieldLabel>
                  <Input
                    value={row.reason}
                    onChange={(e) =>
                      setDeductions((prev) =>
                        prev.map((r, i) => (i === idx ? { ...r, reason: e.target.value } : r))
                      )
                    }
                    placeholder="Clear reason for this deduction..."
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-white/10">
            <div>
              <FieldLabel hint="leave blank to match calculated net">Jeweller Final Offer (INR)</FieldLabel>
              <Input
                type="number"
                step="0.01"
                value={offeredValue}
                onChange={(e) => setOfferedValue(e.target.value)}
                placeholder="Auto-matches calculated net if blank"
              />
            </div>
            <div>
              <FieldLabel>Offer Difference Explanation (If Offer Differs)</FieldLabel>
              <Input
                value={offerDiffExplanation}
                onChange={(e) => setOfferDiffExplanation(e.target.value)}
                placeholder="Explain any rounding or customer-agreed adjustment"
              />
            </div>
          </div>

          <div>
            <FieldLabel>Internal / Customer Notes</FieldLabel>
            <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </Card>

        {/* Live Valuation & Deduction Intelligence Preview */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Button type="button" variant="secondary" onClick={runPreview} disabled={previewLoading}>
            <Calculator className="h-4 w-4 text-[#D4AF37]" />
            {previewLoading ? "Running Valuation & Intelligence..." : "Run Live Valuation & Intelligence Check"}
          </Button>
          <span className="text-xs text-[#9A9AA6]">
            Checks shop policy, missing reasons, rate consistency, and ML baseline.
          </span>
        </div>

        {preview && (
          <div className="space-y-4">
            <ValuationBreakdownCard
              measurement={{
                gross_weight_g: preview.gross_weight_g,
                non_gold_weight_g: preview.non_gold_weight_g,
                net_gold_weight_g: preview.net_gold_weight_g,
                purity_pct: preview.purity_pct,
                purity_karat_label: karatLabel,
                measurement_source: measurementSource,
                instrument_name: instrumentName,
                test_report_ref: testReportRef,
              }}
              rate={{
                rate_24k_per_g: preview.rate_24k_per_g,
                rate_source: rateSource,
              }}
              deductions={deductions.map((d) => ({
                deduction_type: d.deduction_type,
                label: d.label,
                amount_inr: d.amount_inr || "0",
                reason: d.reason,
              }))}
              valuation={{
                pure_gold_weight_g: preview.pure_gold_weight_g,
                gross_reference_value_inr: preview.gross_reference_value_inr,
                total_deductions_inr: preview.total_deductions_inr,
                calculated_net_value_inr: preview.calculated_net_value_inr,
                jeweller_offered_value_inr: preview.jeweller_offered_value_inr,
                offer_difference_inr: preview.offer_difference_inr,
                offer_difference_explanation: offerDiffExplanation,
              }}
              title="Live Valuation Preview"
            />
            <IntelligenceFlagsCard flags={preview.flags} mlStatus={preview.ml_status} />
          </div>
        )}

        {error && (
          <p className="rounded-xl border border-rose-500/35 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        )}
        {offlineSavedMsg && (
          <p className="rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            {offlineSavedMsg}
          </p>
        )}

        <div className="flex flex-col sm:flex-row gap-3">
          <Button type="submit" size="lg" disabled={submitting} className="flex-1">
            <ShieldCheck className="h-5 w-5" />
            {submitting ? "Saving Transaction..." : "Create Gold Exchange Transaction"}
          </Button>
          <Button type="button" size="lg" variant="secondary" onClick={handleSaveOfflineDraft}>
            <CloudOff className="h-5 w-5" />
            Save Offline Draft
          </Button>
        </div>
      </form>
    </AppShell>
  );
}
