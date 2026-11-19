"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  FileSignature,
  GitBranch,
  History,
  ShieldCheck,
} from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime } from "@/lib/i18n";
import { TransactionDetail } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, FieldLabel, Input, Textarea } from "@/components/ui/primitives";
import { ValuationBreakdownCard } from "@/components/valuation/ValuationBreakdownCard";
import { IntelligenceFlagsCard } from "@/components/valuation/IntelligenceFlagsCard";
import { DigitalPassportCard } from "@/components/passport/DigitalPassportCard";

export default function JewellerTransactionDetailPage() {
  const params = useParams<{ id: string }>();
  const txId = params?.id;
  const { user, loading } = useAuth();
  const router = useRouter();

  const [tx, setTx] = useState<TransactionDetail | null>(null);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);

  const [amendOpen, setAmendOpen] = useState(false);
  const [amendReason, setAmendReason] = useState("");
  const [amendOffer, setAmendOffer] = useState("");

  useEffect(() => {
    if (!loading && (!user || user.role !== "jeweller")) {
      router.push("/");
    }
  }, [loading, user, router]);

  const loadDetail = useCallback(async () => {
    if (!txId || !user) return;
    setFetching(true);
    try {
      const data = await apiRequest<TransactionDetail>(`/api/transactions/${txId}`);
      setTx(data);
      if (data.valuation) {
        setAmendOffer(data.valuation.jeweller_offered_value_inr);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load transaction.");
    } finally {
      setFetching(false);
    }
  }, [txId, user]);

  useEffect(() => {
    if (user?.role === "jeweller") loadDetail();
  }, [user, loadDetail]);

  const handleAcknowledge = async () => {
    if (!tx) return;
    setActionBusy(true);
    setError(null);
    try {
      const updated = await apiRequest<TransactionDetail>(`/api/transactions/${tx.id}/acknowledge`, {
        method: "POST",
        body: JSON.stringify({ method: "in_app_confirmation" }),
      });
      setTx(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Acknowledgement failed.");
    } finally {
      setActionBusy(false);
    }
  };

  const handleIssuePassport = async () => {
    if (!tx) return;
    setActionBusy(true);
    setError(null);
    try {
      const updated = await apiRequest<TransactionDetail>(`/api/passports/${tx.id}/issue`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setTx(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not issue Digital Gold Passport.");
    } finally {
      setActionBusy(false);
    }
  };

  const handleCreateAmendment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tx || !tx.measurement || !tx.rate || !tx.valuation) return;
    setActionBusy(true);
    setError(null);
    try {
      const amended = await apiRequest<TransactionDetail>(`/api/transactions/${tx.id}/amend`, {
        method: "POST",
        body: JSON.stringify({
          amendment_reason: amendReason,
          updated_payload: {
            customer_name: tx.customer.full_name,
            customer_mobile: tx.customer.mobile_number,
            customer_preferred_language: tx.customer.preferred_language,
            consent_granted: true,
            item_description: tx.jewellery_items[0]?.item_description || "Gold Item",
            category: tx.jewellery_items[0]?.category || "ornament",
            hallmark_huid: tx.jewellery_items[0]?.hallmark_huid || null,
            stone_or_non_gold_description: tx.jewellery_items[0]?.stone_or_non_gold_description || null,
            gross_weight_g: tx.measurement.gross_weight_g,
            non_gold_weight_g: tx.measurement.non_gold_weight_g,
            net_gold_weight_g: tx.measurement.net_gold_weight_g,
            purity_pct: tx.measurement.purity_pct,
            purity_karat_label: tx.measurement.purity_karat_label,
            measurement_source: tx.measurement.measurement_source,
            instrument_name: tx.measurement.instrument_name,
            test_report_ref: tx.measurement.test_report_ref,
            rate_24k_per_g: tx.rate.rate_24k_per_g,
            rate_source: tx.rate.rate_source,
            is_simulated_rate: tx.rate.is_simulated_rate,
            deductions: tx.deductions.map((d) => ({
              deduction_type: d.deduction_type,
              label: d.label,
              amount_inr: d.amount_inr,
              reason: d.reason || "",
              supporting_doc_ref: d.supporting_doc_ref || null,
            })),
            jeweller_offered_value_inr: amendOffer || tx.valuation.calculated_net_value_inr,
            offer_difference_explanation: "Amended final offer documented with customer review.",
            notes: tx.notes,
            is_demo: tx.is_demo,
          },
        }),
      });
      setAmendOpen(false);
      router.push(`/jeweller/transactions/${amended.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create amendment.");
    } finally {
      setActionBusy(false);
    }
  };

  if (fetching) {
    return (
      <AppShell title="Transaction Details">
        <p className="text-sm text-[#9A9AA6]">Loading transaction record...</p>
      </AppShell>
    );
  }

  if (!tx) {
    return (
      <AppShell title="Transaction Not Found">
        <Card className="space-y-3">
          <p className="text-sm text-rose-300">{error || "Transaction unavailable."}</p>
          <Link href="/jeweller">
            <Button variant="secondary">Back to Dashboard</Button>
          </Link>
        </Card>
      </AppShell>
    );
  }

  const jewellerAck = tx.acknowledgements.find((a) => a.party_role === "jeweller");
  const customerAck = tx.acknowledgements.find((a) => a.party_role === "customer");

  return (
    <AppShell
      title={tx.transaction_code}
      subtitle={`${tx.customer.full_name} · ${tx.customer.mobile_number} · Version ${tx.version_number}`}
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link href="/jeweller" className="inline-flex items-center gap-1.5 text-xs text-[#9A9AA6] hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>

          <div className="flex flex-wrap items-center gap-2">
            {tx.is_demo && <Badge tone="amber">DEMO</Badge>}
            <Badge tone={tx.status === "signed" ? "emerald" : tx.status === "pending_review" ? "amber" : "sky"}>
              {tx.status.replace("_", " ")}
            </Badge>
            {tx.parent_transaction_code && (
              <Badge tone="gold">
                <GitBranch className="h-3 w-3" /> Amended from {tx.parent_transaction_code}
              </Badge>
            )}
          </div>
        </div>

        {error && (
          <p className="rounded-xl border border-rose-500/35 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        )}

        {/* Action Panel: Acknowledgements & Passport Signing */}
        <Card className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-[#F5F5F7]">Acknowledgements &amp; Signing</h2>
              <p className="text-xs text-[#9A9AA6]">
                Signed records are immutable. Corrections create a new linked amendment version.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={jewellerAck ? "emerald" : "neutral"}>
                {jewellerAck ? "Jeweller Acknowledged" : "Jeweller Pending"}
              </Badge>
              <Badge tone={customerAck ? "emerald" : "neutral"}>
                {customerAck ? "Customer Acknowledged" : "Customer Pending"}
              </Badge>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            {!jewellerAck && tx.status !== "signed" && tx.status !== "amended" && (
              <Button onClick={handleAcknowledge} disabled={actionBusy} variant="secondary">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                Jeweller Confirm &amp; Acknowledge
              </Button>
            )}

            {!tx.digital_passport && tx.status !== "amended" && (
              <Button onClick={handleIssuePassport} disabled={actionBusy || !jewellerAck}>
                <FileSignature className="h-4 w-4" />
                Issue Signed Digital Gold Passport
              </Button>
            )}

            {tx.status === "signed" && !tx.amended_by_transaction_code && (
              <Button onClick={() => setAmendOpen((v) => !v)} variant="secondary">
                <GitBranch className="h-4 w-4 text-[#D4AF37]" />
                Create Linked Amendment (v{tx.version_number + 1})
              </Button>
            )}
          </div>

          {amendOpen && (
            <form onSubmit={handleCreateAmendment} className="mt-3 rounded-xl border border-[#D4AF37]/30 bg-[#0B0B0D] p-4 space-y-3">
              <p className="text-xs font-medium text-[#E8D5B5]">
                Original signed record ({tx.transaction_code}) stays immutable; a new linked version will be created.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <FieldLabel required>Amendment Reason</FieldLabel>
                  <Textarea
                    rows={2}
                    required
                    value={amendReason}
                    onChange={(e) => setAmendReason(e.target.value)}
                    placeholder="Reason for creating revised record..."
                  />
                </div>
                <div>
                  <FieldLabel required>Revised Offer (INR)</FieldLabel>
                  <Input
                    type="number"
                    step="0.01"
                    required
                    value={amendOffer}
                    onChange={(e) => setAmendOffer(e.target.value)}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit" size="sm" disabled={actionBusy}>
                  Save Amendment Version
                </Button>
                <Button type="button" size="sm" variant="ghost" onClick={() => setAmendOpen(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          )}
        </Card>

        {/* Signed Digital Passport */}
        {tx.digital_passport && <DigitalPassportCard passport={tx.digital_passport} isDemo={tx.is_demo} />}

        {/* Valuation & Intelligence */}
        {tx.measurement && tx.rate && tx.valuation && (
          <ValuationBreakdownCard
            measurement={tx.measurement}
            rate={tx.rate}
            deductions={tx.deductions}
            valuation={tx.valuation}
          />
        )}

        <IntelligenceFlagsCard flags={tx.anomaly_flags} mlStatus={tx.ml_status} />

        {/* Append-only Audit Trail for this Transaction */}
        <Card className="space-y-3">
          <div className="flex items-center gap-2 border-b border-white/10 pb-2">
            <History className="h-4 w-4 text-[#D4AF37]" />
            <h2 className="text-base font-semibold text-[#F5F5F7]">Transaction Audit History</h2>
          </div>
          <div className="space-y-2">
            {tx.audit_logs.map((log) => (
              <div
                key={log.sequence_number}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 rounded-xl border border-white/8 bg-[#0B0B0D]/70 px-3.5 py-2.5 text-xs"
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-3.5 w-3.5 text-[#D4AF37]" />
                  <span className="font-mono text-[#E8D5B5]">#{log.sequence_number}</span>
                  <span className="font-semibold text-[#F5F5F7]">{log.action}</span>
                  <span className="text-[#9A9AA6]">({log.actor_role})</span>
                </div>
                <div className="flex items-center gap-3 text-[#6E6E7A]">
                  <span className="font-mono">{log.entry_hash.slice(0, 14)}…</span>
                  <span>{formatDateTime(log.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
