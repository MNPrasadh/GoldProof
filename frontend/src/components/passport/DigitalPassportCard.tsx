"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Check, Copy, ExternalLink, Printer, ShieldCheck } from "lucide-react";
import { formatDateTime } from "@/lib/i18n";
import { Badge, Button } from "@/components/ui/primitives";

export function DigitalPassportCard({
  passport,
  isDemo,
}: {
  passport: {
    transaction_code: string;
    version_number: number;
    payload_sha256: string;
    signature_algorithm: string;
    public_key_fingerprint: string;
    verification_url: string;
    qr_data_uri: string;
    signed_at: string;
    is_revoked_by_amendment?: boolean;
  };
  isDemo?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  const copyHash = () => {
    navigator.clipboard?.writeText(passport.payload_sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="passport-surface relative overflow-hidden rounded-2xl p-5 sm:p-6 space-y-5 print-card">
      {/* Subtle metallic gold foil top bar */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#D4AF37] to-transparent opacity-80" />

      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#D4AF37]/40 bg-[#D4AF37]/15">
            <ShieldCheck className="h-5 w-5 text-[#D4AF37]" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-[#F5F5F7]">Digital Gold Passport</h3>
            <p className="text-xs text-[#9A9AA6] font-mono">
              {passport.transaction_code} · v{passport.version_number}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isDemo && <Badge tone="amber">DEMO RECORD</Badge>}
          <Badge tone={passport.is_revoked_by_amendment ? "amber" : "emerald"}>
            {passport.is_revoked_by_amendment
              ? "Superseded by Amendment"
              : `${passport.signature_algorithm} Verified Seal`}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-[176px_1fr] gap-5 items-center">
        <div className="mx-auto text-center space-y-1.5">
          <div className="rounded-2xl border-2 border-[#D4AF37]/40 bg-white p-2.5 shadow-[0_12px_30px_rgba(0,0,0,0.45)]">
            <img
              src={passport.qr_data_uri}
              alt={`QR verification code for ${passport.transaction_code}`}
              className="h-36 w-36 object-contain"
            />
          </div>
          <p className="text-[10px] uppercase tracking-widest text-[#E8D5B5]">Scan to Verify</p>
        </div>

        <div className="space-y-3.5 text-xs">
          <div>
            <p className="uppercase tracking-wider text-[#9A9AA6]">Signed Timestamp</p>
            <p className="mt-0.5 text-sm font-medium text-[#F5F5F7]">{formatDateTime(passport.signed_at)}</p>
          </div>

          <div>
            <p className="uppercase tracking-wider text-[#9A9AA6]">SHA-256 Record Fingerprint</p>
            <div className="mt-1 flex items-center gap-2">
              <code className="flex-1 truncate rounded-xl border border-white/10 bg-[#0B0B0D]/90 px-3 py-2 font-mono text-[11px] text-[#E8D5B5]">
                {passport.payload_sha256}
              </code>
              <button
                type="button"
                onClick={copyHash}
                className="min-h-[36px] px-2.5 inline-flex items-center gap-1 rounded-xl border border-white/12 bg-white/5 text-[#9A9AA6] hover:text-white transition-colors cursor-pointer"
                title="Copy SHA-256"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-[11px] text-emerald-300">Copied</span>
                  </>
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
          </div>

          <p className="text-[11px] leading-relaxed text-[#9A9AA6]">
            Signing key fingerprint:{" "}
            <span className="font-mono text-[#E8D5B5]">{passport.public_key_fingerprint}</span>. A valid
            signature proves this digital record has not changed since signing; it does not independently
            verify manual readings.
          </p>

          <div className="no-print flex flex-wrap gap-2 pt-1">
            <Link href={`/verify/${passport.transaction_code}`}>
              <Button size="sm" variant="primary">
                <ExternalLink className="h-3.5 w-3.5" />
                Open Public Verification
              </Button>
            </Link>
            <Button size="sm" variant="secondary" onClick={() => window.print()}>
              <Printer className="h-3.5 w-3.5" />
              Print / Save PDF
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
