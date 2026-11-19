"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  FilePlus2,
  Languages,
  LayoutDashboard,
  LogOut,
  QrCode,
  RefreshCw,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { t } from "@/lib/i18n";
import { loadOfflineDrafts, OfflineDraftItem, syncPendingDrafts } from "@/lib/offline-store";
import { Button } from "@/components/ui/primitives";
import { OfflineDraftsDrawer } from "@/components/offline/OfflineDraftsDrawer";

function GoldProofMark() {
  return (
    <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-[#D4AF37]/45 bg-gradient-to-br from-[#D4AF37]/25 via-[#D4AF37]/10 to-transparent shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
        <path
          d="M12 2.5L19.5 6.2V12.2C19.5 16.9 16.3 20.6 12 21.8C7.7 20.6 4.5 16.9 4.5 12.2V6.2L12 2.5Z"
          stroke="#D4AF37"
          strokeWidth="1.6"
          fill="rgba(212,175,55,0.12)"
        />
        <path d="M12 7.2L15.6 11.4L12 15.6L8.4 11.4L12 7.2Z" fill="#E8D5B5" />
      </svg>
    </div>
  );
}

export function AppShell({
  children,
  title,
  subtitle,
}: {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
}) {
  const { user, language, setLanguage, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [isOnline, setIsOnline] = useState(true);
  const [drafts, setDrafts] = useState<OfflineDraftItem[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    setIsOnline(typeof navigator !== "undefined" ? navigator.onLine : true);
    const refreshDrafts = () => setDrafts(loadOfflineDrafts());
    refreshDrafts();

    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);

    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    window.addEventListener("goldproof-drafts-changed", refreshDrafts);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("goldproof-drafts-changed", refreshDrafts);
    };
  }, []);

  const pendingCount = drafts.filter((d) => d.sync_status === "pending" || d.sync_status === "conflict").length;

  const handleSync = async () => {
    if (!isOnline || syncing) return;
    setSyncing(true);
    try {
      const updated = await syncPendingDrafts();
      setDrafts(updated);
    } finally {
      setSyncing(false);
    }
  };

  const navItems =
    user?.role === "jeweller"
      ? [
          { href: "/jeweller", label: t(language, "dashboard"), icon: LayoutDashboard },
          { href: "/jeweller/new", label: t(language, "newExchange"), icon: FilePlus2 },
          { href: "/jeweller/ocr", label: t(language, "ocrImport"), icon: ScanLine },
          { href: "/jeweller/analytics", label: t(language, "analytics"), icon: BarChart3 },
          { href: "/verify", label: t(language, "verifyQr"), icon: QrCode },
        ]
      : user?.role === "customer"
      ? [
          { href: "/customer", label: t(language, "myExchanges"), icon: LayoutDashboard },
          { href: "/verify", label: t(language, "verifyQr"), icon: QrCode },
        ]
      : user?.role === "admin"
      ? [
          { href: "/admin", label: t(language, "adminOps"), icon: ShieldCheck },
          { href: "/verify", label: t(language, "verifyQr"), icon: QrCode },
        ]
      : [{ href: "/verify", label: t(language, "verifyQr"), icon: QrCode }];

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .slice(0, 2)
        .map((n) => n[0])
        .join("")
        .toUpperCase()
    : "";

  return (
    <div className="min-h-screen text-[#F5F5F7] pb-28 md:pb-12">
      {/* Sleek Demo Transparency Strip */}
      {(!user || user.is_demo) && (
        <div className="no-print border-b border-[#D4AF37]/20 bg-[#121116]/90 px-4 py-1.5 text-center text-[11px] font-medium text-[#E8D5B5]/90 flex items-center justify-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-[#D4AF37]" />
          <span>{t(language, "demoBanner")}</span>
        </div>
      )}

      {/* Header */}
      <header className="no-print sticky top-0 z-30 border-b border-white/[0.08] bg-[#0B0B0D]/80 backdrop-blur-2xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <GoldProofMark />
            <div>
              <span className="text-base font-semibold tracking-tight text-[#F5F5F7]">
                Gold<span className="text-[#D4AF37]">Proof</span>
              </span>
              {user?.jeweller_profile && (
                <p className="hidden sm:block text-[11px] text-[#9A9AA6] truncate max-w-[200px]">
                  {user.jeweller_profile.shop_name}
                </p>
              )}
            </div>
          </Link>

          {/* Desktop Pill Navigation */}
          <nav className="hidden md:flex items-center gap-1 rounded-2xl border border-white/[0.07] bg-white/[0.03] p-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href + "/"));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-medium transition-all ${
                    active
                      ? "bg-[#D4AF37]/16 text-[#E8D5B5] border border-[#D4AF37]/30 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
                      : "text-[#9A9AA6] hover:text-[#F5F5F7] hover:bg-white/[0.05] border border-transparent"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${active ? "text-[#D4AF37]" : ""}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Controls */}
          <div className="flex items-center gap-2">
            <div
              className={`hidden sm:inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                isOnline
                  ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-200"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${isOnline ? "bg-emerald-400" : "bg-amber-400"}`} />
              {isOnline ? t(language, "online") : t(language, "offline")}
            </div>

            {user?.role === "jeweller" && pendingCount > 0 && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setDrawerOpen(true)}
                className="border-[#D4AF37]/35 text-[#E8D5B5]"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
                <span className="tabular-nums">{pendingCount}</span>
              </Button>
            )}

            <button
              type="button"
              onClick={() => setLanguage(language === "en" ? "ta" : "en")}
              className="min-h-[38px] inline-flex items-center gap-1.5 rounded-xl border border-white/12 bg-white/[0.05] px-3 py-1.5 text-xs font-medium text-[#E8D5B5] hover:bg-white/[0.1] transition-colors cursor-pointer"
              title="Switch Language / மொழி மாற்றம்"
            >
              <Languages className="h-3.5 w-3.5 text-[#D4AF37]" />
              <span>{language === "en" ? "தமிழ்" : "EN"}</span>
            </button>

            {user && (
              <div className="flex items-center gap-1.5">
                <div className="hidden lg:flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-2.5 py-1">
                  <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-[#D4AF37]/20 text-[10px] font-bold text-[#E8D5B5]">
                    {initials}
                  </span>
                  <span className="text-xs text-[#9A9AA6] capitalize">{user.role}</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    router.push("/");
                  }}
                  className="min-h-[38px] inline-flex items-center gap-1.5 rounded-xl border border-white/10 px-2.5 py-1.5 text-xs text-[#9A9AA6] hover:text-[#F5F5F7] hover:bg-white/[0.06] transition-colors cursor-pointer"
                  title={t(language, "signOut")}
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span className="hidden xl:inline">{t(language, "signOut")}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl px-4 py-5 sm:py-8 animate-fade-in">
        {(title || subtitle) && (
          <div className="mb-6 sm:mb-7 flex flex-col gap-1.5">
            {title && (
              <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#F5F5F7]">{title}</h1>
            )}
            {subtitle && <p className="text-sm text-[#9A9AA6] max-w-3xl">{subtitle}</p>}
          </div>
        )}
        {children}
      </main>

      {/* Floating Mobile Frosted Bottom Dock */}
      <nav className="no-print md:hidden fixed bottom-2.5 left-3 right-3 z-30 rounded-2xl border border-white/14 bg-[#121216]/92 backdrop-blur-2xl px-2 py-1 shadow-[0_14px_36px_rgba(0,0,0,0.75)]">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href + "/"));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex min-h-[48px] min-w-[56px] flex-col items-center justify-center gap-1 rounded-xl px-2.5 py-1 text-[10px] font-medium transition-colors ${
                  active ? "text-[#D4AF37]" : "text-[#9A9AA6]"
                }`}
              >
                {active && (
                  <span className="absolute top-0.5 h-0.5 w-5 rounded-full bg-[#D4AF37]" />
                )}
                <Icon className="h-4 w-4" />
                <span className="truncate max-w-[74px]">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {drawerOpen && (
        <OfflineDraftsDrawer
          drafts={drafts}
          isOnline={isOnline}
          syncing={syncing}
          onSync={handleSync}
          onClose={() => setDrawerOpen(false)}
          onChanged={() => setDrafts(loadOfflineDrafts())}
        />
      )}
    </div>
  );
}
