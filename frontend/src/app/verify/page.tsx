"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { QrCode, Search, ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Button, Card, Input } from "@/components/ui/primitives";
import { QrScannerModal } from "@/components/passport/QrScannerModal";

export default function VerifyIndexPage() {
  const router = useRouter();
  const [code, setCode] = useState("GP-DEMO-2026-001");
  const [scannerOpen, setScannerOpen] = useState(false);

  return (
    <AppShell
      title="Verify a Digital Gold Passport"
      subtitle="Enter any GoldProof transaction code or scan the customer receipt QR code to cryptographically verify integrity."
    >
      <Card className="max-w-xl mx-auto space-y-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[#D4AF37]/40 bg-[#D4AF37]/15">
            <ShieldCheck className="h-6 w-6 text-[#D4AF37]" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-[#F5F5F7]">Public Cryptographic Verification</h2>
            <p className="text-xs text-[#9A9AA6]">Checks Ed25519 signature, SHA-256 hash, and record immutability.</p>
          </div>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (code.trim()) router.push(`/verify/${encodeURIComponent(code.trim())}`);
          }}
          className="space-y-3"
        >
          <Input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="e.g. GP-DEMO-2026-001"
          />
          <div className="flex flex-col sm:flex-row gap-2.5">
            <Button type="submit" className="flex-1">
              <Search className="h-4 w-4" />
              Verify Passport
            </Button>
            <Button type="button" variant="secondary" onClick={() => setScannerOpen(true)}>
              <QrCode className="h-4 w-4" />
              Scan Camera QR
            </Button>
          </div>
        </form>
      </Card>

      {scannerOpen && <QrScannerModal onClose={() => setScannerOpen(false)} />}
    </AppShell>
  );
}
