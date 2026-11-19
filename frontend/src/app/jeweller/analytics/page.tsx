"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatGrams, formatINR } from "@/lib/i18n";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Card, Select, Skeleton } from "@/components/ui/primitives";

interface JewellerAnalyticsData {
  shop_name: string;
  days_window: number;
  summary: {
    total_transactions: number;
    total_gold_weight_g: string;
    total_exchange_value_inr: string;
    average_deduction_inr: string;
    average_deduction_pct: string;
    transactions_requiring_review: number;
    signed_passports_count: number;
    missing_reason_frequency: number;
    policy_mismatch_frequency: number;
    rate_inconsistency_frequency: number;
    instrument_evidence_completeness_pct: number;
  };
  ml_readiness: {
    enabled: boolean;
    non_demo_sample_count: number;
    min_samples_required: number;
    note: string;
  };
  daily_trends: { date: string; count: number; exchange_value_inr: number; deductions_inr: number }[];
  monthly_trends: { month: string; count: number; exchange_value_inr: number; gold_weight_g: number }[];
}

export default function JewellerAnalyticsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [days, setDays] = useState("90");
  const [statusFilter, setStatusFilter] = useState("all");
  const [data, setData] = useState<JewellerAnalyticsData | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "jeweller")) {
      router.push("/");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user || user.role !== "jeweller") return;
    apiRequest<JewellerAnalyticsData>(
      `/api/analytics/jeweller?days=${days}&status=${encodeURIComponent(statusFilter)}`
    ).then(setData);
  }, [user, days, statusFilter]);

  if (loading || !user || user.role !== "jeweller" || !data) {
    return (
      <AppShell title="Shop Analytics">
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Skeleton className="h-72 w-full" />
            <Skeleton className="h-72 w-full" />
          </div>
        </div>
      </AppShell>
    );
  }

  const s = data.summary;

  return (
    <AppShell
      title="Jeweller Analytics"
      subtitle={`Strictly isolated metrics for ${data.shop_name} — private customer records are never shared across shops.`}
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Badge tone={data.ml_readiness.enabled ? "emerald" : "sky"}>
            ML Isolation Forest: {data.ml_readiness.note}
          </Badge>
          <div className="flex gap-2">
            <Select value={days} onChange={(e) => setDays(e.target.value)} className="w-36">
              <option value="7">Last 7 Days</option>
              <option value="30">Last 30 Days</option>
              <option value="90">Last 90 Days</option>
              <option value="365">Last 1 Year</option>
            </Select>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
              <option value="all">All Statuses</option>
              <option value="signed">Signed Only</option>
              <option value="pending_review">Review Required</option>
              <option value="pending_acknowledgement">Pending Ack</option>
            </Select>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <Card className="p-4">
            <p className="text-xs text-[#9A9AA6]">Average Deduction</p>
            <p className="mt-1.5 text-xl font-semibold tabular-nums text-[#F5F5F7]">
              {formatINR(s.average_deduction_inr)}
            </p>
            <p className="text-xs text-[#D4AF37] tabular-nums">{s.average_deduction_pct}% of gross</p>
          </Card>

          <Card className="p-4">
            <p className="text-xs text-[#9A9AA6]">Missing-Reason Frequency</p>
            <p className="mt-1.5 text-xl font-semibold tabular-nums text-amber-300">
              {s.missing_reason_frequency}
            </p>
            <p className="text-xs text-[#6E6E7A]">Transactions lacking deduction reason</p>
          </Card>

          <Card className="p-4">
            <p className="text-xs text-[#9A9AA6]">Policy Mismatch Frequency</p>
            <p className="mt-1.5 text-xl font-semibold tabular-nums text-amber-300">
              {s.policy_mismatch_frequency}
            </p>
            <p className="text-xs text-[#6E6E7A]">Rate inconsistencies: {s.rate_inconsistency_frequency}</p>
          </Card>

          <Card className="p-4">
            <p className="text-xs text-[#9A9AA6]">Instrument Evidence Completeness</p>
            <p className="mt-1.5 text-xl font-semibold tabular-nums text-emerald-300">
              {s.instrument_evidence_completeness_pct}%
            </p>
            <p className="text-xs text-[#6E6E7A]">
              Total net gold: {formatGrams(s.total_gold_weight_g)}
            </p>
          </Card>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="space-y-3">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Daily Exchange Value vs Deductions (INR)</h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.daily_trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="date" stroke="#9A9AA6" fontSize={11} />
                  <YAxis stroke="#9A9AA6" fontSize={11} />
                  <Tooltip
                    formatter={(val: number) => formatINR(val)}
                    contentStyle={{
                      backgroundColor: "#141418",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: "12px",
                      fontSize: "12px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="exchange_value_inr"
                    name="Exchange Value"
                    stroke="#D4AF37"
                    fill="rgba(212,175,55,0.22)"
                  />
                  <Area
                    type="monotone"
                    dataKey="deductions_inr"
                    name="Deductions"
                    stroke="#f87171"
                    fill="rgba(248,113,113,0.16)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card className="space-y-3">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Monthly Gold Volume (Grams)</h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.monthly_trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="month" stroke="#9A9AA6" fontSize={11} />
                  <YAxis stroke="#9A9AA6" fontSize={11} />
                  <Tooltip
                    formatter={(val: number) => `${Number(val).toFixed(3)} g`}
                    contentStyle={{
                      backgroundColor: "#141418",
                      border: "1px solid rgba(255,255,255,0.12)",
                      borderRadius: "12px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="gold_weight_g" name="Net Gold (g)" fill="#E8D5B5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
