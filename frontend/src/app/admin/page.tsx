"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Link2, ShieldAlert, ShieldCheck, Store } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime, formatGrams, formatINR } from "@/lib/i18n";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Card, Skeleton } from "@/components/ui/primitives";

interface AdminAnalytics {
  system_summary: {
    total_jeweller_shops: number;
    total_transactions: number;
    signed_transactions: number;
    transactions_requiring_review: number;
    total_gold_weight_g: string;
    total_exchange_value_inr: string;
  };
  audit_chain_integrity: {
    valid: boolean;
    total_entries: number;
    first_broken_sequence: number | null;
  };
  shop_summaries: {
    shop_name: string;
    shop_code: string;
    city: string;
    transaction_count: number;
    signed_count: number;
    review_required_count: number;
    total_exchange_value_inr: string;
  }[];
  recent_audit_logs: {
    sequence_number: number;
    action: string;
    actor_role: string;
    transaction_id: string | null;
    entry_hash: string;
    previous_log_hash: string;
    created_at: string;
  }[];
}

export default function AdminDashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<AdminAnalytics | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) {
      router.push("/");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (user?.role === "admin") {
      apiRequest<AdminAnalytics>("/api/analytics/admin").then(setData);
    }
  }, [user]);

  if (loading || !user || user.role !== "admin" || !data) {
    return (
      <AppShell title="Platform Governance & Audit">
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </AppShell>
    );
  }

  const s = data.system_summary;

  return (
    <AppShell
      title="Administrator Trust & Audit Console"
      subtitle="Aggregate shop compliance metrics and append-only SHA-256 chained audit verification."
    >
      <div className="space-y-6">
        {/* Audit Integrity Banner */}
        <Card
          className={`flex flex-wrap items-center justify-between gap-3 ${
            data.audit_chain_integrity.valid
              ? "border-emerald-500/35 bg-emerald-950/20"
              : "border-rose-500/50 bg-rose-950/25"
          }`}
        >
          <div className="flex items-center gap-3">
            {data.audit_chain_integrity.valid ? (
              <ShieldCheck className="h-7 w-7 text-emerald-400" />
            ) : (
              <ShieldAlert className="h-7 w-7 text-rose-400" />
            )}
            <div>
              <h2 className="text-base font-semibold text-[#F5F5F7]">
                Append-Only Audit Hash Chain:{" "}
                {data.audit_chain_integrity.valid ? "Verified Intact" : "Chain Broken"}
              </h2>
              <p className="text-xs text-[#9A9AA6]">
                {data.audit_chain_integrity.total_entries} sequential cryptographic audit records checked.
              </p>
            </div>
          </div>
          <Badge tone={data.audit_chain_integrity.valid ? "emerald" : "rose"}>
            {data.audit_chain_integrity.valid ? "Hash Chain Valid" : "Tamper Detected"}
          </Badge>
        </Card>

        {/* System Aggregates */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <Card className="p-4">
            <p className="text-xs text-[#9A9AA6]">Registered Jeweller Shops</p>
            <p className="mt-1.5 text-2xl font-semibold tabular-nums">{s.total_jeweller_shops}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-[#9A9AA6]">Total Platform Transactions</p>
            <p className="mt-1.5 text-2xl font-semibold tabular-nums">{s.total_transactions}</p>
            <p className="text-xs text-emerald-300">{s.signed_transactions} signed</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-[#9A9AA6]">Total Gold Processed</p>
            <p className="mt-1.5 text-2xl font-semibold tabular-nums text-[#E8D5B5]">
              {formatGrams(s.total_gold_weight_g)}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-xs text-[#9A9AA6]">Total Exchange Volume</p>
            <p className="mt-1.5 text-xl font-semibold tabular-nums text-[#D4AF37]">
              {formatINR(s.total_exchange_value_inr)}
            </p>
          </Card>
        </div>

        {/* Shop Summaries */}
        <Card className="space-y-3">
          <div className="flex items-center gap-2 border-b border-white/10 pb-2">
            <Store className="h-4 w-4 text-[#D4AF37]" />
            <h2 className="text-base font-semibold">Tenant Shop Compliance Overview</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.shop_summaries.map((shop) => (
              <div key={shop.shop_code} className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-4 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-[#F5F5F7]">{shop.shop_name}</span>
                  <Badge tone="neutral">{shop.shop_code}</Badge>
                </div>
                <p className="text-xs text-[#9A9AA6]">{shop.city}</p>
                <div className="pt-2 flex flex-wrap gap-3 text-xs tabular-nums">
                  <span>Tx: {shop.transaction_count}</span>
                  <span className="text-emerald-300">Signed: {shop.signed_count}</span>
                  <span className="text-amber-300">Review: {shop.review_required_count}</span>
                  <span className="text-[#D4AF37]">{formatINR(shop.total_exchange_value_inr)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Recent Append-Only Audit Log Explorer */}
        <Card className="space-y-3">
          <h2 className="text-base font-semibold border-b border-white/10 pb-2">
            Recent Append-Only Audit Events
          </h2>
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {data.recent_audit_logs.map((log) => (
              <div
                key={log.sequence_number}
                className="rounded-xl border border-white/8 bg-[#0B0B0D]/75 px-3.5 py-2.5 text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[#D4AF37]">#{log.sequence_number}</span>
                  <span className="font-semibold text-[#F5F5F7]">{log.action}</span>
                  <Badge tone="neutral">{log.actor_role}</Badge>
                </div>
                <div className="flex flex-wrap items-center gap-2.5 text-[#9A9AA6]">
                  <span className="inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/[0.03] px-2 py-0.5 font-mono text-[10px]">
                    <Link2 className="h-3 w-3 text-[#D4AF37]" />
                    {log.previous_log_hash.slice(0, 8)} → {log.entry_hash.slice(0, 12)}
                  </span>
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
