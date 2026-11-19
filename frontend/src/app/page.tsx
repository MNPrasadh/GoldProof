"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Lock,
  QrCode,
  Scale,
  ShieldCheck,
  Sparkles,
  Store,
  UserCheck,
  UserPlus,
  Users,
} from "lucide-react";
import { apiRequest, setStoredToken } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { t } from "@/lib/i18n";
import { DemoAccount, User } from "@/lib/types";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, FieldLabel, Input, Select, Skeleton } from "@/components/ui/primitives";
import { QrScannerModal } from "@/components/passport/QrScannerModal";

export default function HomePage() {
  const { user, language, loginWithCredentials, refreshUser } = useAuth();
  const router = useRouter();

  const [demoAccounts, setDemoAccounts] = useState<DemoAccount[]>([]);
  const [loadingDemos, setLoadingDemos] = useState(true);
  const [authTab, setAuthTab] = useState<"signin" | "register">("signin");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [regName, setRegName] = useState("");
  const [regPhone, setRegPhone] = useState("");
  const [regRole, setRegRole] = useState<"customer" | "jeweller">("customer");
  const [regShopName, setRegShopName] = useState("");
  const [regLang, setRegLang] = useState<"en" | "ta">("ta");

  const [authError, setAuthError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [verifyCode, setVerifyCode] = useState("GP-DEMO-2026-001");
  const [scannerOpen, setScannerOpen] = useState(false);

  useEffect(() => {
    apiRequest<DemoAccount[]>("/api/auth/demo-accounts", { skipAuth: true })
      .then(setDemoAccounts)
      .catch(() => setDemoAccounts([]))
      .finally(() => setLoadingDemos(false));
  }, []);

  const routeByRole = (role: string) => {
    if (role === "jeweller") router.push("/jeweller");
    else if (role === "customer") router.push("/customer");
    else if (role === "admin") router.push("/admin");
  };

  const handleLogin = async (targetEmail: string, targetPass: string) => {
    setAuthError(null);
    setSubmitting(true);
    try {
      const loggedIn = await loginWithCredentials(targetEmail, targetPass);
      routeByRole(loggedIn.role);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setSubmitting(true);
    try {
      const resp = await apiRequest<{ access_token: string; user: User }>("/api/auth/register", {
        method: "POST",
        skipAuth: true,
        body: JSON.stringify({
          email,
          password,
          full_name: regName,
          phone: regPhone || null,
          role: regRole,
          preferred_language: regLang,
          shop_name: regRole === "jeweller" ? regShopName || `${regName} Jewellers` : null,
        }),
      });
      setStoredToken(resp.access_token);
      await refreshUser();
      routeByRole(resp.user.role);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Editorial 12-Column Luxury Hero */}
        <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-[#17161D] via-[#101015] to-[#0B0B0D] p-6 sm:p-10 shadow-[0_24px_60px_-20px_rgba(0,0,0,0.8)]">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left 7 Cols */}
            <div className="lg:col-span-7 space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="gold">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Ed25519 Signed Passports
                </Badge>
                <Badge tone="neutral">தமிழ் &amp; English Voice AI</Badge>
                <Badge tone="neutral">Offline-Ready PWA</Badge>
              </div>

              <div className="space-y-2.5">
                <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight text-[#F5F5F7] leading-[1.08]">
                  Gold<span className="text-[#D4AF37]">Proof</span>
                  <span className="block text-xl sm:text-2xl font-normal text-[#E8D5B5] mt-2">
                    Transparent Gold Exchange. Verified by Math &amp; Cryptography.
                  </span>
                </h1>
                <p className="text-sm text-[#9A9AA6] max-w-xl leading-relaxed">
                  {t(language, "tagline")} Independent 24K equivalent calculations, neutral AI deduction
                  intelligence, Tamil &amp; English voice explanations, and QR Digital Gold Passports.
                </p>
              </div>

              {/* Unified Public Verification Command Bar */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (verifyCode.trim()) router.push(`/verify/${encodeURIComponent(verifyCode.trim())}`);
                }}
                className="rounded-2xl border border-white/12 bg-[#0B0B0D]/85 p-2 flex flex-col sm:flex-row gap-2 max-w-xl shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
              >
                <Input
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value)}
                  placeholder="Passport Code (e.g. GP-DEMO-2026-001)"
                  className="border-0 bg-transparent shadow-none focus:ring-0"
                />
                <div className="flex gap-2 shrink-0">
                  <Button type="button" variant="secondary" onClick={() => setScannerOpen(true)}>
                    <QrCode className="h-4 w-4 text-[#D4AF37]" />
                    Scan
                  </Button>
                  <Button type="submit">
                    Verify
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </form>

              {user && (
                <div>
                  <Button onClick={() => routeByRole(user.role)} variant="secondary">
                    Continue as {user.full_name} ({user.role})
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>

            {/* Right 5 Cols: Live Specimen Digital Gold Passport */}
            <div className="lg:col-span-5">
              <Link
                href="/verify/GP-DEMO-2026-001"
                className="block passport-surface rounded-2xl p-5 space-y-4 hover:border-[#D4AF37]/55 transition-all group"
              >
                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-[0.18em] text-[#D4AF37]">
                      Specimen Digital Gold Passport
                    </p>
                    <p className="mt-0.5 font-mono text-xs font-semibold text-[#F5F5F7]">GP-DEMO-2026-001</p>
                  </div>
                  <Badge tone="emerald">
                    <ShieldCheck className="h-3 w-3" />
                    Ed25519 Verified
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="rounded-xl bg-[#0B0B0D]/70 border border-white/8 p-2.5">
                    <p className="text-[10px] text-[#9A9AA6]">Net Gold</p>
                    <p className="mt-0.5 font-semibold tabular-nums text-[#F5F5F7]">20.000 g</p>
                    <p className="text-[10px] text-[#6E6E7A]">22K · 91.6%</p>
                  </div>
                  <div className="rounded-xl bg-[#0B0B0D]/70 border border-white/8 p-2.5">
                    <p className="text-[10px] text-[#9A9AA6]">24K Pure Eq</p>
                    <p className="mt-0.5 font-semibold tabular-nums text-[#E8D5B5]">18.320 g</p>
                    <p className="text-[10px] text-[#6E6E7A]">₹7,600/g</p>
                  </div>
                  <div className="rounded-xl bg-[#0B0B0D]/70 border border-white/8 p-2.5">
                    <p className="text-[10px] text-[#9A9AA6]">Deductions</p>
                    <p className="mt-0.5 font-semibold tabular-nums text-rose-300">-₹3,000</p>
                    <p className="text-[10px] text-[#6E6E7A]">2 documented</p>
                  </div>
                </div>

                <div className="flex items-end justify-between border-t border-white/10 pt-3">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#9A9AA6]">
                      Verified Exchange Value
                    </p>
                    <p className="text-2xl font-bold tabular-nums text-[#D4AF37]">₹1,36,232.00</p>
                  </div>
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-[#E8D5B5] group-hover:translate-x-0.5 transition-transform">
                    Inspect Proof <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </Link>
            </div>
          </div>
        </section>

        {/* Main Grid: Demo Quick Access + Sign In / Register */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* 1-Tap Demo Accounts */}
          <Card className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <h2 className="text-lg font-semibold text-[#F5F5F7]">Instant Demo Portals</h2>
                <p className="text-xs text-[#9A9AA6]">
                  1-tap role sign-in for Jeweller, Customer (தமிழ் / English), Tenant Isolation, and Admin.
                </p>
              </div>
              <Badge tone="amber">DEMO MODE</Badge>
            </div>

            {loadingDemos ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-36 w-full" />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {demoAccounts.map((acc) => {
                  const Icon =
                    acc.role === "jeweller" ? Store : acc.role === "customer" ? Users : UserCheck;
                  return (
                    <button
                      key={acc.email}
                      type="button"
                      disabled={submitting}
                      onClick={() => handleLogin(acc.email, acc.password)}
                      className="group text-left rounded-2xl border border-white/10 bg-[#0B0B0D]/80 p-4 hover:border-[#D4AF37]/50 hover:bg-[#16161D] hover:-translate-y-[1px] transition-all cursor-pointer flex flex-col justify-between gap-3"
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#D4AF37]/30 bg-[#D4AF37]/10 group-hover:bg-[#D4AF37]/20 transition-colors">
                            <Icon className="h-4 w-4 text-[#D4AF37]" />
                          </div>
                          <Badge tone={acc.role === "customer" ? "emerald" : acc.role === "admin" ? "sky" : "gold"}>
                            {acc.role}
                          </Badge>
                        </div>
                        <h3 className="text-sm font-semibold text-[#F5F5F7] group-hover:text-[#E8D5B5]">
                          {acc.label}
                        </h3>
                        <p className="text-xs text-[#9A9AA6] leading-relaxed">{acc.description}</p>
                      </div>
                      <div className="flex items-center justify-between pt-2.5 border-t border-white/8 text-[11px] text-[#9A9AA6]">
                        <span className="font-mono truncate">{acc.email}</span>
                        <span className="text-[#D4AF37] font-medium flex items-center gap-1 shrink-0 group-hover:translate-x-0.5 transition-transform">
                          Enter <ArrowRight className="h-3 w-3" />
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Standard Sign-In / Create Account */}
          <Card className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                {authTab === "signin" ? (
                  <Lock className="h-4 w-4 text-[#D4AF37]" />
                ) : (
                  <UserPlus className="h-4 w-4 text-[#D4AF37]" />
                )}
                <h2 className="text-lg font-semibold text-[#F5F5F7]">
                  {authTab === "signin" ? "Account Sign In" : "Create Account"}
                </h2>
              </div>

              <div className="flex rounded-xl border border-white/10 bg-[#0B0B0D] p-0.5 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setAuthTab("signin");
                    setAuthError(null);
                  }}
                  className={`rounded-lg px-2.5 py-1 font-medium cursor-pointer transition-colors ${
                    authTab === "signin" ? "bg-[#D4AF37] text-[#0B0B0D]" : "text-[#9A9AA6] hover:text-white"
                  }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthTab("register");
                    setAuthError(null);
                  }}
                  className={`rounded-lg px-2.5 py-1 font-medium cursor-pointer transition-colors ${
                    authTab === "register" ? "bg-[#D4AF37] text-[#0B0B0D]" : "text-[#9A9AA6] hover:text-white"
                  }`}
                >
                  Register
                </button>
              </div>
            </div>

            {authTab === "signin" ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleLogin(email, password);
                }}
                className="space-y-4"
              >
                <div>
                  <FieldLabel required>Email</FieldLabel>
                  <Input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                  />
                </div>
                <div>
                  <FieldLabel required>Password</FieldLabel>
                  <Input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>

                {authError && (
                  <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                    {authError}
                  </p>
                )}

                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? "Signing in..." : "Sign In"}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="space-y-3">
                <div className="grid grid-cols-2 gap-2.5">
                  <div>
                    <FieldLabel required>Role</FieldLabel>
                    <Select
                      value={regRole}
                      onChange={(e) => setRegRole(e.target.value as "customer" | "jeweller")}
                    >
                      <option value="customer">Customer</option>
                      <option value="jeweller">Jeweller</option>
                    </Select>
                  </div>
                  <div>
                    <FieldLabel>Language</FieldLabel>
                    <Select value={regLang} onChange={(e) => setRegLang(e.target.value as "en" | "ta")}>
                      <option value="ta">தமிழ் (Tamil)</option>
                      <option value="en">English</option>
                    </Select>
                  </div>
                </div>
                <div>
                  <FieldLabel required>Full Name</FieldLabel>
                  <Input required value={regName} onChange={(e) => setRegName(e.target.value)} />
                </div>
                {regRole === "jeweller" && (
                  <div>
                    <FieldLabel required>Jewellery Shop Name</FieldLabel>
                    <Input required value={regShopName} onChange={(e) => setRegShopName(e.target.value)} />
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <FieldLabel required>Email</FieldLabel>
                    <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
                  </div>
                  <div>
                    <FieldLabel>Mobile</FieldLabel>
                    <Input value={regPhone} onChange={(e) => setRegPhone(e.target.value)} placeholder="+91..." />
                  </div>
                </div>
                <div>
                  <FieldLabel required hint="min 8 chars">Password</FieldLabel>
                  <Input
                    type="password"
                    minLength={8}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>

                {authError && (
                  <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
                    {authError}
                  </p>
                )}

                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? "Creating account..." : "Create Account"}
                </Button>
              </form>
            )}

            <div className="border-t border-white/10 pt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-xl bg-[#0B0B0D]/70 p-2.5 border border-white/8">
                <Scale className="h-4 w-4 text-[#D4AF37] mx-auto mb-1" />
                <p className="text-[11px] text-[#9A9AA6]">24K Pure Math</p>
              </div>
              <div className="rounded-xl bg-[#0B0B0D]/70 p-2.5 border border-white/8">
                <Sparkles className="h-4 w-4 text-[#D4AF37] mx-auto mb-1" />
                <p className="text-[11px] text-[#9A9AA6]">Neutral AI Rules</p>
              </div>
              <div className="rounded-xl bg-[#0B0B0D]/70 p-2.5 border border-white/8">
                <ShieldCheck className="h-4 w-4 text-[#D4AF37] mx-auto mb-1" />
                <p className="text-[11px] text-[#9A9AA6]">Ed25519 QR</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {scannerOpen && <QrScannerModal onClose={() => setScannerOpen(false)} />}
    </AppShell>
  );
}
