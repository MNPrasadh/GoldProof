"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, CheckCircle2, FileUp, ScanLine } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, FieldLabel, Input, Select } from "@/components/ui/primitives";

interface OcrResponse {
  provider: string;
  is_simulated: boolean;
  requires_human_confirmation: boolean;
  confidence: number;
  raw_text: string;
  warning: string;
  extracted_fields: {
    document_type?: string;
    item_description?: string;
    gross_weight_g?: string | null;
    non_gold_weight_g?: string | null;
    net_gold_weight_g?: string | null;
    purity_pct?: string | null;
    rate_24k_per_g?: string | null;
    test_report_ref?: string | null;
    instrument_name?: string | null;
  };
}

export default function JewellerOcrPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [documentType, setDocumentType] = useState("assay_report");
  const [file, setFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [result, setResult] = useState<OcrResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [confirmed, setConfirmed] = useState(false);
  const [itemDesc, setItemDesc] = useState("");
  const [grossWeight, setGrossWeight] = useState("");
  const [nonGoldWeight, setNonGoldWeight] = useState("0.00");
  const [purityPct, setPurityPct] = useState("");
  const [rate24k, setRate24k] = useState("7600.00");
  const [reportRef, setReportRef] = useState("");
  const [instrumentName, setInstrumentName] = useState("");

  useEffect(() => {
    if (!loading && (!user || user.role !== "jeweller")) {
      router.push("/");
    }
  }, [loading, user, router]);

  const runExtraction = async (chosenFile?: File) => {
    const targetFile = chosenFile || file;
    if (!targetFile) {
      setError("Select a register, receipt, or assay report file first (or use Sample Slip).");
      return;
    }
    setError(null);
    setConfirmed(false);
    setExtracting(true);
    try {
      const form = new FormData();
      form.append("document_type", documentType);
      form.append("file", targetFile);
      const res = await apiRequest<OcrResponse>("/api/ocr/extract", {
        method: "POST",
        body: form,
      });
      setResult(res);
      setItemDesc(res.extracted_fields.item_description || "");
      setGrossWeight(res.extracted_fields.gross_weight_g || "");
      setNonGoldWeight(res.extracted_fields.non_gold_weight_g || "0.00");
      setPurityPct(res.extracted_fields.purity_pct || "");
      setRate24k(res.extracted_fields.rate_24k_per_g || "7600.00");
      setReportRef(res.extracted_fields.test_report_ref || "");
      setInstrumentName(res.extracted_fields.instrument_name || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "OCR extraction failed.");
    } finally {
      setExtracting(false);
    }
  };

  const runSampleDemoSlip = async () => {
    const sampleBlob = new Blob(
      [
        `GOLD ASSAY & EXCHANGE SLIP\nReport Ref: XRF-2026-884\nItem: 22K Gold Bangle Pair\nGross Weight: 18.40 g\nPurity: 91.6 %\n24K Rate: 7600.00`,
      ],
      { type: "text/plain" }
    );
    const sampleFile = new File([sampleBlob], "sample_assay_slip.txt", { type: "text/plain" });
    setFile(sampleFile);
    await runExtraction(sampleFile);
  };

  const proceedToTransaction = () => {
    if (!confirmed) return;
    sessionStorage.setItem(
      "goldproof_ocr_prefill",
      JSON.stringify({
        item_description: itemDesc,
        gross_weight_g: grossWeight,
        non_gold_weight_g: nonGoldWeight,
        purity_pct: purityPct,
        rate_24k_per_g: rate24k,
        test_report_ref: reportRef,
        instrument_name: instrumentName,
      })
    );
    router.push("/jeweller/new");
  };

  return (
    <AppShell
      title="OCR Document Intelligence"
      subtitle="Extract fields from handwritten registers, paper receipts, or assay slips with mandatory human verification."
    >
      <div className="space-y-6">
        <Card className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <FieldLabel>Document Type</FieldLabel>
              <Select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
                <option value="assay_report">Gold Testing / Assay Report</option>
                <option value="handwritten_register">Old Handwritten Transaction Register</option>
                <option value="paper_receipt">Paper Exchange Receipt</option>
                <option value="valuation_document">Valuation Document</option>
              </Select>
            </div>
            <div>
              <FieldLabel>Upload Document Image / Text Slip</FieldLabel>
              <input
                type="file"
                accept="image/*,.txt,.pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full min-h-[44px] rounded-xl border border-white/12 bg-[#101014] px-3 py-2 text-xs text-[#9A9AA6] file:mr-3 file:rounded-lg file:border-0 file:bg-[#D4AF37]/20 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-[#E8D5B5]"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button onClick={() => runExtraction()} disabled={extracting}>
              <ScanLine className="h-4 w-4" />
              {extracting ? "Extracting Fields..." : "Run OCR Extraction"}
            </Button>
            <Button type="button" variant="secondary" onClick={runSampleDemoSlip} disabled={extracting}>
              <FileUp className="h-4 w-4" />
              Test with Sample Slip
            </Button>
          </div>

          {error && <p className="text-xs text-rose-300">{error}</p>}
        </Card>

        {result && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-2">
                <h2 className="text-base font-semibold text-[#F5F5F7]">Extracted Raw Text</h2>
                <div className="flex items-center gap-2">
                  <Badge tone={result.is_simulated ? "amber" : "emerald"}>
                    {result.is_simulated ? "Simulated OCR Adapter" : result.provider}
                  </Badge>
                  <Badge tone="neutral">Conf: {Math.round(result.confidence * 100)}%</Badge>
                </div>
              </div>
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200 flex gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{result.warning}</span>
              </div>
              <pre className="rounded-xl border border-white/10 bg-[#0B0B0D] p-3.5 text-xs text-[#E8D5B5] whitespace-pre-wrap font-mono">
                {result.raw_text}
              </pre>
            </Card>

            <Card className="space-y-4">
              <h2 className="text-base font-semibold text-[#F5F5F7] border-b border-white/10 pb-2">
                Human Confirmation Required Before Saving
              </h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <FieldLabel>Item Description</FieldLabel>
                  <Input value={itemDesc} onChange={(e) => setItemDesc(e.target.value)} />
                </div>
                <div>
                  <FieldLabel>Gross Weight (g)</FieldLabel>
                  <Input value={grossWeight} onChange={(e) => setGrossWeight(e.target.value)} />
                </div>
                <div>
                  <FieldLabel>Non-Gold Weight (g)</FieldLabel>
                  <Input value={nonGoldWeight} onChange={(e) => setNonGoldWeight(e.target.value)} />
                </div>
                <div>
                  <FieldLabel>Purity (%)</FieldLabel>
                  <Input value={purityPct} onChange={(e) => setPurityPct(e.target.value)} />
                </div>
                <div>
                  <FieldLabel>24K Rate (INR/g)</FieldLabel>
                  <Input value={rate24k} onChange={(e) => setRate24k(e.target.value)} />
                </div>
                <div>
                  <FieldLabel>Report Reference</FieldLabel>
                  <Input value={reportRef} onChange={(e) => setReportRef(e.target.value)} />
                </div>
                <div>
                  <FieldLabel>Instrument Name</FieldLabel>
                  <Input value={instrumentName} onChange={(e) => setInstrumentName(e.target.value)} />
                </div>
              </div>

              <label className="flex items-start gap-3 rounded-xl border border-[#D4AF37]/30 bg-[#D4AF37]/8 p-3 text-xs text-[#E8D5B5] cursor-pointer">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                  className="mt-0.5 h-5 w-5 shrink-0 accent-[#D4AF37]"
                />
                <span>
                  I have visually checked every extracted value above against the physical paper document.
                </span>
              </label>

              <Button onClick={proceedToTransaction} disabled={!confirmed} className="w-full">
                <CheckCircle2 className="h-4 w-4" />
                Load Confirmed Fields into New Transaction
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Card>
          </div>
        )}
      </div>
    </AppShell>
  );
}
