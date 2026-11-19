"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  Info,
  Printer,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { apiRequest } from "@/lib/api";
import { formatDateTime } from "@/lib/i18n";
import { PassportVerificationResponse } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, Skeleton } from "@/components/ui/primitives";
import { ValuationBreakdownCard } from "@/components/valuation/ValuationBreakdownCard";

export default function VerifyPassportCodePage() {
  const params = useParams<{ code: string }>();
  const code = decodeURIComponent(params?.code || "");

  const [data, setData] = useState<PassportVerificationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedSha, setCopiedSha] = useState(false);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    apiRequest<PassportVerificationResponse>(`/api/passports/verify/${encodeURIComponent(code)}`, {
      skipAuth: true,
    })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Verification failed."))
      .finally(() => setLoading(false));
  }, [code]);

  if (loading) {
    return (
      <AppShell title="Verifying Digital Gold Passport">
        <div className="space-y-4">
          <Skeleton className="h-44 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AppShell>
    );
  }

  if (error || !data) {
    return (
      <AppShell title="Passport Not Found">
        <Card className="max-w-lg mx-auto space-y-4">
          <div className="flex items-center gap-2 text-rose-300">
            <ShieldAlert className="h-5 w-5" />
            <h2 className="text-base font-semibold">Unable to Verify Passport</h2>
          </div>
          <p className="text-sm text-[#9A9AA6]">{error || "No passport exists for this code."}</p>
          <Link href="/verify">
            <Button variant="secondary">Try Another Code</Button>
          </Link>
        </Card>
      </AppShell>
    );
  }

  const isVerified = data.integrity_status === "verified";
  const isSuperseded = data.integrity_status === "superseded_by_amendment";

  const copySha = () => {
    navigator.clipboard?.writeText(data.payload_sha256);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 1800);
  };

  return (
    <AppShell
      title={`Digital Gold Passport · ${data.transaction_code}`}
      subtitle={`${data.jeweller.shop_name} (${data.jeweller.city}, ${data.jeweller.state}) · Version ${data.version_number}`}
    >
      <div className="space-y-6">
        {/* Cryptographic Verification Banner */}
        <Card
          className={`space-y-4 print-card ${
            isVerified
              ? "border-emerald-500/45 bg-gradient-to-br from-emerald-950/30 via-[#121614] to-[#0E0F12]"
              : isSuperseded
              ? "border-amber-500/45 bg-gradient-to-br from-amber-950/30 via-[#161412] to-[#0E0F12]"
              : "border-rose-500/55 bg-gradient-to-br from-rose-950/35 via-[#181214] to-[#0E0F12]"
          }`}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3.5">
              <div
                className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border ${
                  isVerified
                    ? "border-emerald-400/40 bg-emerald-500/15 text-emerald-300"
                    : isSuperseded
                    ? "border-amber-400/40 bg-amber-500/15 text-amber-300"
                    : "border-rose-400/40 bg-rose-500/15 text-rose-300"
                }`}
              >
                {isVerified ? (
                  <ShieldCheck className="h-7 w-7" />
                ) : isSuperseded ? (
                  <AlertTriangle className="h-7 w-7" />
                ) : (
                  <ShieldAlert className="h-7 w-7" />
                )}
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg sm:text-xl font-semibold text-[#F5F5F7]">
                    {isVerified
                      ? "Cryptographically Verified"
                      : isSuperseded
                      ? "Historical Version — Amended"
                      : "Integrity Tamper Alert"}
                  </h2>
                  {data.is_demo && <Badge tone="amber">DEMO RECORD</Badge>}
                </div>
                <p className="mt-1 text-sm text-[#E8D5B5]">{data.integrity_message}</p>
              </div>
            </div>

            <Button size="sm" variant="secondary" className="no-print" onClick={() => window.print()}>
              <Printer className="h-4 w-4" />
              Print Receipt
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
            <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-3">
              <p className="text-[#9A9AA6]">Ed25519 Signature</p>
              <p className={`mt-1 font-semibold ${data.signature_valid ? "text-emerald-300" : "text-rose-300"}`}>
                {data.signature_valid ? "Valid Signature ✓" : "Invalid Signature ✗"}
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-3">
              <p className="text-[#9A9AA6]">Record Unchanged Since Signing</p>
              <p
                className={`mt-1 font-semibold ${
                  data.matches_current_db_record ? "text-emerald-300" : "text-rose-300"
                }`}
              >
                {data.matches_current_db_record ? "Exact Match ✓" : "Mismatch Detected ✗"}
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-3">
              <p className="text-[#9A9AA6]">Signed At</p>
              <p className="mt-1 font-semibold text-[#F5F5F7]">{formatDateTime(data.signed_at)}</p>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-3 text-xs text-[#9A9AA6] flex gap-2">
            <Info className="h-4 w-4 text-[#D4AF37] shrink-0 mt-0.5" />
            <span>{data.verification_scope_notice}</span>
          </div>

          {data.amended_by_transaction_code && (
            <div className="text-xs text-amber-200">
              A newer linked version exists:{" "}
              <Link href={`/verify/${data.amended_by_transaction_code}`} className="underline font-semibold">
                {data.amended_by_transaction_code}
              </Link>
            </div>
          )}
        </Card>

        {/* Customer & Shop Identity */}
        <Card className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs print-card">
          <div>
            <p className="uppercase tracking-wider text-[#9A9AA6]">Customer</p>
            <p className="mt-1 text-sm font-semibold text-[#F5F5F7]">{data.customer_display.full_name}</p>
            <p className="text-[#9A9AA6]">{data.customer_display.masked_mobile}</p>
          </div>
          <div>
            <p className="uppercase tracking-wider text-[#9A9AA6]">Ornament</p>
            <p className="mt-1 text-sm font-semibold text-[#F5F5F7]">
              {data.jewellery_items[0]?.item_description}
            </p>
            <p className="text-[#9A9AA6]">
              {data.jewellery_items[0]?.hallmark_huid ? `HUID: ${data.jewellery_items[0].hallmark_huid}` : "Standard ornament"}
            </p>
          </div>
          <div>
            <p className="uppercase tracking-wider text-[#9A9AA6]">Acknowledgements</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {data.acknowledgements.map((ack) => (
                <Badge key={ack.party_role} tone="emerald">
                  <CheckCircle2 className="h-3 w-3" />
                  {ack.party_role}: {ack.acknowledged_by_name}
                </Badge>
              ))}
            </div>
          </div>
        </Card>

        {/* Full Valuation Breakdown */}
        <ValuationBreakdownCard
          measurement={data.measurement}
          rate={data.rate}
          deductions={data.deductions}
          valuation={data.valuation}
        />

        {/* Cryptographic Proofs & QR */}
        <Card className="passport-surface grid grid-cols-1 sm:grid-cols-[170px_1fr] gap-5 items-center print-card">
          <div className="mx-auto rounded-2xl border-2 border-[#D4AF37]/35 bg-white p-2">
            <img src={data.qr_data_uri} alt="Verification QR" className="h-32 w-32 object-contain" />
          </div>
          <div className="space-y-2.5 text-xs">
            <p className="uppercase tracking-wider text-[#9A9AA6]">SHA-256 Canonical Digest</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 break-all rounded-xl border border-white/10 bg-[#0B0B0D]/90 p-2.5 font-mono text-[11px] text-[#E8D5B5]">
                {data.payload_sha256}
              </code>
              <button
                type="button"
                onClick={copySha}
                className="min-h-[36px] px-2.5 inline-flex items-center gap-1 rounded-xl border border-white/12 bg-white/5 text-[#9A9AA6] hover:text-white cursor-pointer shrink-0"
              >
                {copiedSha ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
            <p className="text-[#9A9AA6]">
              Public Key Fingerprint: <span className="font-mono text-[#F5F5F7]">{data.public_key_fingerprint}</span> ·
              Algorithm: {data.signature_algorithm}
            </p>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
