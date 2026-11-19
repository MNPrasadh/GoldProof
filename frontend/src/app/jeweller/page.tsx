"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowUpRight,
  Coins,
  FilePlus2,
  QrCode,
  ReceiptText,
  Scale,
  ScanLine,
  Search,
  ShieldCheck,
} from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime, formatGrams, formatINR, t } from "@/lib/i18n";
import { TransactionSummary } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, Input, Skeleton } from "@/components/ui/primitives";

interface JewellerAnalyticsOverview {
  summary: {
    total_transactions: number;
    total_gold_weight_g: string;
    total_exchange_value_inr: string;
    transactions_requiring_review: number;
    signed_passports_count: number;
  };
  daily_trends: { date: string; count: number; exchange_value_inr: number }[];
}

export default function JewellerDashboardPage() {
  const { user, loading, language } = useAuth();
  const router = useRouter();
  const [transactions, setTransactions] = useState<TransactionSummary[]>([]);
  const [analytics, setAnalytics] = useState<JewellerAnalyticsOverview | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!loading && (!user || user.role !== "jeweller")) {
      router.push("/");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user || user.role !== "jeweller") return;
    setFetching(true);
    Promise.all([
      apiRequest<TransactionSummary[]>(
        `/api/transactions?status=${encodeURIComponent(statusFilter)}&search=${encodeURIComponent(search)}`
      ),
      apiRequest<JewellerAnalyticsOverview>("/api/analytics/jeweller?days=90"),
    ])
      .then(([txList, analyticsData]) => {
        setTransactions(txList);
        setAnalytics(analyticsData);
      })
      .finally(() => setFetching(false));
  }, [user, statusFilter, search]);

  if (loading || !user || user.role !== "jeweller") {
    return (
      <AppShell title="Jeweller Dashboard">
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </AppShell>
    );
  }

  const summary = analytics?.summary;

  return (
    <AppShell
      title={user.jeweller_profile?.shop_name || "Jeweller Workspace"}
      subtitle={`${user.jeweller_profile?.city || ""}, ${user.jeweller_profile?.state || ""} · Shop Code ${user.jeweller_profile?.shop_code || ""}`}
    >
      <div className="space-y-6">
        {/* Quick Action Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <Link href="/jeweller/new">
              <Button>
                <FilePlus2 className="h-4 w-4" />
                {t(language, "newExchange")}
              </Button>
            </Link>
            <Link href="/jeweller/ocr">
              <Button variant="secondary">
                <ScanLine className="h-4 w-4 text-[#D4AF37]" />
                OCR Paper Slip / Report
              </Button>
            </Link>
          </div>
          <Link
            href="/jeweller/analytics"
            className="text-xs font-medium text-[#D4AF37] hover:text-[#E8D5B5] flex items-center gap-1 transition-colors"
          >
            Open Full Shop Analytics <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <Card className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">
                {t(language, "totalTransactions")}
              </p>
              <ReceiptText className="h-4 w-4 text-[#D4AF37]" />
            </div>
            <p className="text-2xl sm:text-3xl font-semibold tabular-nums text-[#F5F5F7]">
              {summary?.total_transactions ?? transactions.length}
            </p>
            <p className="text-xs text-emerald-300 tabular-nums">
              {summary?.signed_passports_count ?? 0} signed passports
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">
                {t(language, "totalGoldWeight")}
              </p>
              <Scale className="h-4 w-4 text-[#D4AF37]" />
            </div>
            <p className="text-2xl sm:text-3xl font-semibold tabular-nums text-[#E8D5B5]">
              {formatGrams(summary?.total_gold_weight_g ?? "0")}
            </p>
            <p className="text-xs text-[#9A9AA6]">Net gold-bearing weight</p>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">
                {t(language, "totalExchangeValue")}
              </p>
              <Coins className="h-4 w-4 text-[#D4AF37]" />
            </div>
            <p className="text-xl sm:text-2xl font-semibold tabular-nums text-[#D4AF37]">
              {formatINR(summary?.total_exchange_value_inr ?? "0")}
            </p>
            <p className="text-xs text-[#9A9AA6]">Offered exchange total</p>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">
                {t(language, "reviewRequired")}
              </p>
              <AlertTriangle className="h-4 w-4 text-amber-300" />
            </div>
            <p className="text-2xl sm:text-3xl font-semibold tabular-nums text-amber-300">
              {summary?.transactions_requiring_review ?? 0}
            </p>
            <p className="text-xs text-[#9A9AA6]">Flagged by Deduction Intelligence</p>
          </Card>
        </div>

        {/* Compact Exchange Activity Chart */}
        {analytics && analytics.daily_trends.length > 0 && (
          <Card className="p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[#9A9AA6]">
                Recent Daily Exchange Activity (INR)
              </h2>
              <span className="text-[11px] text-[#E8D5B5]">90-day window</span>
            </div>
            <div className="h-28 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.daily_trends}>
                  <XAxis dataKey="date" stroke="#6E6E7A" fontSize={10} tickLine={false} axisLine={false} />
                  <Tooltip
                    formatter={(val: number) => formatINR(val)}
                    contentStyle={{
                      backgroundColor: "#141418",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: "10px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="exchange_value_inr" name="Exchange Value" fill="#D4AF37" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}

        {/* Transactions Ledger */}
        <Card className="p-4 sm:p-5 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
            <h2 className="text-base font-semibold text-[#F5F5F7]">{t(language, "recentTransactions")}</h2>
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative">
                <Search className="h-4 w-4 text-[#6E6E7A] absolute left-3 top-3" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search code, customer, ornament..."
                  className="pl-9 sm:w-64"
                />
              </div>
              <div className="flex gap-1.5 overflow-x-auto pb-1 sm:pb-0">
                {[
                  { key: "all", label: "All" },
                  { key: "pending_review", label: "Review" },
                  { key: "pending_acknowledgement", label: "Pending Ack" },
                  { key: "signed", label: "Signed" },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setStatusFilter(tab.key)}
                    className={`min-h-[38px] rounded-xl px-3 text-xs font-medium whitespace-nowrap transition-colors cursor-pointer ${
                      statusFilter === tab.key
                        ? "bg-[#D4AF37] text-[#0B0B0D] font-semibold"
                        : "bg-white/[0.05] text-[#9A9AA6] hover:text-white"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {fetching ? (
            <div className="space-y-2.5">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : transactions.length === 0 ? (
            <div className="py-10 text-center space-y-3">
              <p className="text-sm text-[#9A9AA6]">No transactions match your filter.</p>
              <Link href="/jeweller/new">
                <Button size="sm">Create Gold Exchange</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-2.5">
              {transactions.map((tx) => {
                const accentBorder =
                  tx.status === "signed"
                    ? "border-l-emerald-400"
                    : tx.status === "pending_review"
                    ? "border-l-amber-400"
                    : "border-l-sky-400";
                return (
                  <Link
                    key={tx.id}
                    href={`/jeweller/transactions/${tx.id}`}
                    className={`block rounded-2xl border border-white/10 border-l-[3px] ${accentBorder} bg-[#0B0B0D]/80 p-4 hover:border-[#D4AF37]/45 hover:bg-[#14141A] transition-all`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-xs font-semibold text-[#D4AF37]">
                            {tx.transaction_code}
                          </span>
                          {tx.is_demo && <Badge tone="amber">DEMO</Badge>}
                          <Badge
                            tone={
                              tx.status === "signed"
                                ? "emerald"
                                : tx.status === "pending_review"
                                ? "amber"
                                : "sky"
                            }
                          >
                            {tx.status === "signed" && <ShieldCheck className="h-3 w-3" />}
                            {tx.status === "pending_review" && <AlertTriangle className="h-3 w-3" />}
                            {tx.status.replace("_", " ")}
                          </Badge>
                          {tx.has_passport && (
                            <Badge tone="gold">
                              <QrCode className="h-3 w-3" /> QR Passport
                            </Badge>
                          )}
                          <Badge tone="neutral">{tx.measurement_source.replace("_", " ")}</Badge>
                        </div>
                        <p className="text-sm font-medium text-[#F5F5F7]">
                          {tx.customer_name} · <span className="text-[#9A9AA6]">{tx.item_description}</span>
                        </p>
                        <p className="text-xs text-[#9A9AA6] tabular-nums">
                          Net {formatGrams(tx.net_gold_weight_g)} · {tx.purity_pct}% ({tx.purity_karat_label}) ·{" "}
                          {formatDateTime(tx.created_at)}
                        </p>
                      </div>

                      <div className="sm:text-right shrink-0 space-y-1">
                        <p className="text-lg font-semibold tabular-nums text-[#F5F5F7]">
                          {formatINR(tx.jeweller_offered_value_inr)}
                        </p>
                        <p className="text-xs text-[#9A9AA6] tabular-nums">
                          Deductions: {formatINR(tx.total_deductions_inr)}
                          {tx.review_flag_count > 0 && (
                            <span className="ml-2 text-amber-300">· {tx.review_flag_count} flag(s)</span>
                          )}
                        </p>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
