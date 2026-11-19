"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, Mic, QrCode, ShieldCheck } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime, formatGrams, formatINR, t } from "@/lib/i18n";
import { TransactionSummary } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, Skeleton } from "@/components/ui/primitives";
import { QrScannerModal } from "@/components/passport/QrScannerModal";

export default function CustomerPortalPage() {
  const { user, loading, language } = useAuth();
  const router = useRouter();
  const [transactions, setTransactions] = useState<TransactionSummary[]>([]);
  const [fetching, setFetching] = useState(true);
  const [scannerOpen, setScannerOpen] = useState(false);

  useEffect(() => {
    if (!loading && (!user || user.role !== "customer")) {
      router.push("/");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user || user.role !== "customer") return;
    apiRequest<TransactionSummary[]>("/api/transactions")
      .then(setTransactions)
      .finally(() => setFetching(false));
  }, [user]);

  if (loading || !user || user.role !== "customer") {
    return (
      <AppShell title={t(language, "myExchanges")}>
        <div className="space-y-3">
          <Skeleton className="h-14 w-64" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title={language === "ta" ? `வணக்கம், ${user.full_name}` : `Welcome, ${user.full_name}`}
      subtitle={
        language === "ta"
          ? "உங்கள் தங்கப் பரிமாற்ற மதிப்பு, கழிவுகள் மற்றும் டிஜிட்டல் பாஸ்போர்ட் விவரங்களைத் தெளிவாகப் பாருங்கள்."
          : "View your gold purity, weights, deductions, and verifiable Digital Gold Passports."
      }
    >
      <div className="space-y-6">
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => setScannerOpen(true)} size="lg">
            <QrCode className="h-5 w-5" />
            {t(language, "scanQr")}
          </Button>
          {transactions[0] && (
            <Link href={`/customer/transactions/${transactions[0].id}`}>
              <Button variant="secondary" size="lg">
                <Mic className="h-5 w-5 text-[#D4AF37]" />
                {language === "ta" ? "தமிழில் கேள்வி கேட்க" : "Ask Voice AI Assistant"}
              </Button>
            </Link>
          )}
        </div>

        {fetching ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : transactions.length === 0 ? (
          <Card className="py-10 text-center text-sm text-[#9A9AA6]">
            No gold exchange records linked to your account yet.
          </Card>
        ) : (
          <div className="space-y-3.5">
            {transactions.map((tx) => {
              const statusLabel =
                tx.status === "signed"
                  ? language === "ta"
                    ? "கையொப்பமிடப்பட்டு சரிபார்க்கப்பட்டது"
                    : "Signed & Verifiable"
                  : tx.status === "pending_review"
                  ? language === "ta"
                    ? "விளக்கம் / சரிபார்ப்பு தேவை"
                    : "Review Recommended"
                  : language === "ta"
                  ? "உங்கள் ஒப்புதல் காத்திருக்கிறது"
                  : "Waiting for Your Confirmation";

              const accentBorder =
                tx.status === "signed"
                  ? "border-l-emerald-400"
                  : tx.status === "pending_review"
                  ? "border-l-amber-400"
                  : "border-l-sky-400";

              return (
                <Link key={tx.id} href={`/customer/transactions/${tx.id}`} className="block">
                  <Card interactive className={`border-l-[3px] ${accentBorder} space-y-3`}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-[#D4AF37]">
                          {tx.transaction_code}
                        </span>
                        {tx.is_demo && <Badge tone="amber">DEMO</Badge>}
                      </div>
                      <Badge
                        tone={
                          tx.status === "signed"
                            ? "emerald"
                            : tx.status === "pending_review"
                            ? "amber"
                            : "sky"
                        }
                      >
                        {tx.status === "signed" ? (
                          <ShieldCheck className="h-3 w-3" />
                        ) : (
                          <AlertCircle className="h-3 w-3" />
                        )}
                        {statusLabel}
                      </Badge>
                    </div>

                    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
                      <div>
                        <h3 className="text-base font-semibold text-[#F5F5F7]">{tx.item_description}</h3>
                        <p className="text-xs text-[#9A9AA6] mt-0.5">
                          {tx.shop_name} · {formatGrams(tx.net_gold_weight_g)} ({tx.purity_pct}% ·{" "}
                          {tx.purity_karat_label})
                        </p>
                        <p className="text-[11px] text-[#6E6E7A] mt-0.5">{formatDateTime(tx.created_at)}</p>
                      </div>

                      <div className="sm:text-right">
                        <p className="text-[11px] uppercase tracking-wider text-[#9A9AA6]">
                          {language === "ta" ? "இறுதி வழங்கல்" : "Final Exchange Value"}
                        </p>
                        <p className="text-2xl font-bold tabular-nums text-[#D4AF37]">
                          {formatINR(tx.jeweller_offered_value_inr)}
                        </p>
                        <span className="inline-flex items-center gap-1 text-xs text-[#E8D5B5] mt-1">
                          {language === "ta" ? "முழு கணக்கீடு & குரல் உதவி" : "View Breakdown & Ask AI"}{" "}
                          <ArrowRight className="h-3.5 w-3.5" />
                        </span>
                      </div>
                    </div>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {scannerOpen && <QrScannerModal onClose={() => setScannerOpen(false)} />}
    </AppShell>
  );
}
