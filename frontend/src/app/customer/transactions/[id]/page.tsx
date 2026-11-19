"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Printer, Share2, ShieldCheck } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime, formatINR, t } from "@/lib/i18n";
import { TransactionDetail } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, Skeleton } from "@/components/ui/primitives";
import { ValuationBreakdownCard } from "@/components/valuation/ValuationBreakdownCard";
import { IntelligenceFlagsCard } from "@/components/valuation/IntelligenceFlagsCard";
import { DigitalPassportCard } from "@/components/passport/DigitalPassportCard";
import { VoiceAssistantPanel } from "@/components/assistant/VoiceAssistantPanel";

export default function CustomerTransactionDetailPage() {
  const params = useParams<{ id: string }>();
  const txId = params?.id;
  const { user, loading, language } = useAuth();
  const router = useRouter();

  const [tx, setTx] = useState<TransactionDetail | null>(null);
  const [fetching, setFetching] = useState(true);
  const [ackBusy, setAckBusy] = useState(false);
  const [shareNote, setShareNote] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "customer")) {
      router.push("/");
    }
  }, [loading, user, router]);

  const loadDetail = useCallback(async () => {
    if (!txId || !user) return;
    setFetching(true);
    try {
      const data = await apiRequest<TransactionDetail>(`/api/transactions/${txId}`);
      setTx(data);
    } finally {
      setFetching(false);
    }
  }, [txId, user]);

  useEffect(() => {
    if (user?.role === "customer") loadDetail();
  }, [user, loadDetail]);

  const handleCustomerAck = async () => {
    if (!tx) return;
    setAckBusy(true);
    try {
      const updated = await apiRequest<TransactionDetail>(`/api/transactions/${tx.id}/acknowledge`, {
        method: "POST",
        body: JSON.stringify({ method: "customer_portal_confirmation" }),
      });
      setTx(updated);
    } finally {
      setAckBusy(false);
    }
  };

  const handleShareReceipt = async () => {
    if (!tx) return;
    const shareUrl = tx.digital_passport?.verification_url || window.location.href;
    if (navigator.share) {
      await navigator
        .share({
          title: `GoldProof Receipt ${tx.transaction_code}`,
          text: `Verified gold exchange valuation for ${tx.transaction_code}`,
          url: shareUrl,
        })
        .catch(() => undefined);
    } else {
      await navigator.clipboard?.writeText(shareUrl);
      setShareNote("Verification link copied to clipboard.");
      setTimeout(() => setShareNote(null), 2500);
    }
  };

  if (fetching || !tx) {
    return (
      <AppShell title="Gold Exchange Details">
        <div className="space-y-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AppShell>
    );
  }

  const customerAck = tx.acknowledgements.find((a) => a.party_role === "customer");
  const jewellerAck = tx.acknowledgements.find((a) => a.party_role === "jeweller");
  const bothAcked = Boolean(customerAck && jewellerAck);
  const isSigned = Boolean(tx.digital_passport);

  const trustSteps = [
    {
      label: language === "ta" ? "அளவீடு & மதிப்பு" : "Measured & Valued",
      done: Boolean(tx.valuation),
    },
    {
      label: language === "ta" ? "இரு தரப்பு ஒப்புதல்" : "Parties Confirmed",
      done: bothAcked,
    },
    {
      label: language === "ta" ? "Ed25519 பாஸ்போர்ட்" : "Ed25519 Signed",
      done: isSigned,
    },
  ];

  const grossNum = Number(tx.valuation?.gross_reference_value_inr || 0);
  const offeredNum = Number(tx.valuation?.jeweller_offered_value_inr || 0);
  const retainedPct = grossNum > 0 ? ((offeredNum / grossNum) * 100).toFixed(1) : "100.0";

  return (
    <AppShell
      title={tx.jewellery_items[0]?.item_description || tx.transaction_code}
      subtitle={`${tx.jeweller.shop_name} · ${tx.transaction_code} · ${formatDateTime(tx.created_at)}`}
    >
      <div className="space-y-6">
        <div className="no-print flex flex-wrap items-center justify-between gap-2">
          <Link href="/customer" className="inline-flex items-center gap-1.5 text-xs text-[#9A9AA6] hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            {t(language, "myExchanges")}
          </Link>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={handleShareReceipt}>
              <Share2 className="h-3.5 w-3.5" />
              Share
            </Button>
            <Button size="sm" variant="secondary" onClick={() => window.print()}>
              <Printer className="h-3.5 w-3.5" />
              Print Receipt
            </Button>
          </div>
        </div>
        {shareNote && <p className="text-xs text-emerald-300">{shareNote}</p>}

        {/* 3-Step Trust Progress Bar */}
        <Card className="p-4">
          <div className="grid grid-cols-3 gap-2">
            {trustSteps.map((step, i) => (
              <div key={step.label} className="flex items-center gap-2">
                <div
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold border ${
                    step.done
                      ? "border-emerald-400/60 bg-emerald-500/20 text-emerald-300"
                      : "border-white/15 bg-white/5 text-[#6E6E7A]"
                  }`}
                >
                  {step.done ? "✓" : i + 1}
                </div>
                <span className={`text-xs font-medium ${step.done ? "text-[#F5F5F7]" : "text-[#6E6E7A]"}`}>
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </Card>

        {/* Hero Summary for Low-Tech-Literacy Clarity */}
        {tx.valuation && (
          <Card className="passport-surface space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs uppercase tracking-wider text-[#E8D5B5]">
                {language === "ta" ? "உங்களுக்குக் கிடைக்கும் இறுதித் தொகை" : "Your Gold Exchange Offer"}
              </span>
              <div className="flex flex-wrap gap-2">
                {tx.is_demo && <Badge tone="amber">DEMO</Badge>}
                <Badge tone="gold">{retainedPct}% Retained</Badge>
                <Badge tone={customerAck ? "emerald" : "amber"}>
                  {customerAck ? t(language, "acknowledgedBadge") : "Confirmation Pending"}
                </Badge>
              </div>
            </div>

            <p className="text-4xl sm:text-5xl font-bold tabular-nums text-[#D4AF37] tracking-tight">
              {formatINR(tx.valuation.jeweller_offered_value_inr)}
            </p>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3 text-xs text-[#9A9AA6]">
              <span>
                Gross Value: <strong className="text-[#F5F5F7]">{formatINR(tx.valuation.gross_reference_value_inr)}</strong> ·
                Total Deductions:{" "}
                <strong className="text-rose-300">{formatINR(tx.valuation.total_deductions_inr)}</strong>
              </span>
              <span className="flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5 text-[#D4AF37]" />
                {jewellerAck ? "Jeweller Confirmed ✓" : "Jeweller Pending"} ·{" "}
                {customerAck ? "Customer Confirmed ✓" : "Customer Pending"}
              </span>
            </div>

            {!customerAck && tx.status !== "signed" && tx.status !== "amended" && (
              <Button onClick={handleCustomerAck} disabled={ackBusy} size="lg" className="w-full sm:w-auto">
                <CheckCircle2 className="h-5 w-5" />
                {ackBusy ? "Confirming..." : t(language, "acknowledgeBtn")}
              </Button>
            )}
          </Card>
        )}

        {/* Prominent Tamil & English Voice AI Assistant */}
        <VoiceAssistantPanel
          transactionId={tx.id}
          defaultLanguage={language === "ta" ? "ta" : tx.customer.preferred_language}
        />

        {/* Transparent Breakdown & Deduction Intelligence */}
        {tx.measurement && tx.rate && tx.valuation && (
          <ValuationBreakdownCard
            measurement={tx.measurement}
            rate={tx.rate}
            deductions={tx.deductions}
            valuation={tx.valuation}
            title={t(language, "valuationTitle")}
          />
        )}

        <IntelligenceFlagsCard flags={tx.anomaly_flags} mlStatus={tx.ml_status} />

        {/* Signed Digital Passport */}
        {tx.digital_passport && <DigitalPassportCard passport={tx.digital_passport} isDemo={tx.is_demo} />}
      </div>
    </AppShell>
  );
}
