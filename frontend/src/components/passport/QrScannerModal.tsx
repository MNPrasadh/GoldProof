"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera, QrCode, Search, X } from "lucide-react";
import { Button, Input } from "@/components/ui/primitives";

export function QrScannerModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [manualCode, setManualCode] = useState("GP-DEMO-2026-001");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraActive, setCameraActive] = useState(false);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let rafId: number | null = null;
    let stopped = false;

    const startCamera = async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          setCameraError("Camera access unavailable in this browser. Enter Transaction ID below.");
          return;
        }
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (stopped || !videoRef.current) return;
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setCameraActive(true);

        const Detector = (window as unknown as { BarcodeDetector?: new (opts: { formats: string[] }) => { detect: (el: HTMLVideoElement) => Promise<{ rawValue: string }[]> } }).BarcodeDetector;
        if (!Detector) {
          setCameraError("Live QR auto-detection is unavailable on this browser; enter code manually below.");
          return;
        }
        const detector = new Detector({ formats: ["qr_code"] });
        const scanLoop = async () => {
          if (stopped || !videoRef.current) return;
          try {
            const codes = await detector.detect(videoRef.current);
            if (codes.length > 0 && codes[0].rawValue) {
              const raw = codes[0].rawValue.trim();
              const extracted = raw.includes("/verify/") ? raw.split("/verify/").pop() || raw : raw;
              onClose();
              router.push(`/verify/${encodeURIComponent(extracted)}`);
              return;
            }
          } catch {
            // keep scanning
          }
          rafId = requestAnimationFrame(scanLoop);
        };
        rafId = requestAnimationFrame(scanLoop);
      } catch {
        setCameraError("Camera permission declined or unavailable. Enter Transaction ID manually below.");
      }
    };

    startCamera();

    return () => {
      stopped = true;
      if (rafId) cancelAnimationFrame(rafId);
      if (stream) {
        stream.getTracks().forEach((tr) => tr.stop());
      }
    };
  }, [onClose, router]);

  const handleManualVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualCode.trim()) return;
    onClose();
    router.push(`/verify/${encodeURIComponent(manualCode.trim())}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl border border-white/15 bg-[#141418] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <QrCode className="h-5 w-5 text-[#D4AF37]" />
            <h3 className="text-base font-semibold text-[#F5F5F7]">Scan Digital Passport QR</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="min-h-[38px] min-w-[38px] flex items-center justify-center rounded-xl text-[#9A9AA6] hover:bg-white/10 hover:text-white cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="relative overflow-hidden rounded-xl border border-white/10 bg-[#0B0B0D] aspect-video flex items-center justify-center">
          <video ref={videoRef} className="h-full w-full object-cover" muted playsInline />
          {!cameraActive && (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
              <Camera className="h-8 w-8 text-[#D4AF37] mb-2" />
              <p className="text-xs text-[#9A9AA6]">{cameraError || "Initializing camera..."}</p>
            </div>
          )}
        </div>

        {cameraError && cameraActive && <p className="text-xs text-amber-300">{cameraError}</p>}

        <form onSubmit={handleManualVerify} className="space-y-2.5 border-t border-white/10 pt-3">
          <p className="text-xs text-[#9A9AA6]">Or verify directly by Transaction Code:</p>
          <div className="flex gap-2">
            <Input
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              placeholder="e.g. GP-DEMO-2026-001"
            />
            <Button type="submit">
              <Search className="h-4 w-4" />
              Verify
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
