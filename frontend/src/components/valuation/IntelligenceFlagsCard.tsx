"use client";

import React from "react";
import { AlertCircle, CheckCircle2, Info, Sparkles } from "lucide-react";
import { AnomalyFlag } from "@/lib/types";
import { Badge, Card } from "@/components/ui/primitives";

export function IntelligenceFlagsCard({
  flags,
  mlStatus,
}: {
  flags: AnomalyFlag[];
  mlStatus?: {
    enabled: boolean;
    sample_count: number;
    min_samples_required: number;
    trained_on_demo_data: boolean;
    reason?: string;
  };
}) {
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[#D4AF37]" />
          <h2 className="text-base font-semibold text-[#F5F5F7]">AI Deduction Intelligence</h2>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="neutral">Deterministic Rules Active</Badge>
          <Badge tone={mlStatus?.enabled ? "emerald" : "sky"}>
            ML Isolation Forest: {mlStatus?.enabled ? "Active" : `${mlStatus?.sample_count ?? 0}/${mlStatus?.min_samples_required ?? 15} real tx`}
          </Badge>
        </div>
      </div>

      {flags.length === 0 ? (
        <div className="flex items-center gap-3 rounded-xl border border-emerald-500/25 bg-emerald-500/10 p-3.5 text-sm text-emerald-200">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
          <span>All recorded deductions, rates, and documentation align with shop policy.</span>
        </div>
      ) : (
        <div className="space-y-2.5">
          {flags.map((flag, idx) => {
            const isReview = flag.severity === "review_required";
            const isAttention = flag.severity === "attention";
            const boxStyle = isReview
              ? "border-amber-500/35 bg-amber-500/10 text-amber-100"
              : isAttention
              ? "border-sky-500/30 bg-sky-500/10 text-sky-100"
              : "border-white/12 bg-white/5 text-[#E8D5B5]";
            return (
              <div key={flag.id || `${flag.code}-${idx}`} className={`rounded-xl border p-3.5 space-y-1.5 ${boxStyle}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {isReview ? (
                      <AlertCircle className="h-4 w-4 text-amber-300 shrink-0" />
                    ) : (
                      <Info className="h-4 w-4 text-sky-300 shrink-0" />
                    )}
                    <span className="text-sm font-semibold">{flag.title}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Badge tone={flag.detection_method === "ml_isolation_forest" ? "gold" : "neutral"}>
                      {flag.detection_method === "ml_isolation_forest" ? "ML Anomaly" : "Rule-Based Check"}
                    </Badge>
                    <Badge tone={isReview ? "amber" : isAttention ? "sky" : "neutral"}>
                      {flag.severity.replace("_", " ")}
                    </Badge>
                  </div>
                </div>
                <p className="text-xs leading-relaxed opacity-90">{flag.message}</p>
              </div>
            );
          })}
        </div>
      )}

      {mlStatus && (
        <p className="text-[11px] text-[#9A9AA6]">
          {mlStatus.reason ||
            `Isolation Forest requires at least ${mlStatus.min_samples_required} non-demo shop transactions (${mlStatus.sample_count} recorded). GoldProof never trains anomaly models on fabricated demo data.`}
        </p>
      )}
    </Card>
  );
}
