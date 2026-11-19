import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: "GoldProof — Transparent Gold Exchange Intelligence",
  description:
    "AI-powered gold exchange intelligence and verifiable Digital Gold Passport platform for India.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "GoldProof",
  },
};

export const viewport: Viewport = {
  themeColor: "#0B0B0D",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0B0B0D] text-[#F5F5F7] font-sans antialiased selection:bg-[#D4AF37]/30 selection:text-[#F5F5F7]">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
