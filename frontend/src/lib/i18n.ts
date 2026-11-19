import { Language } from "./types";

export function formatINR(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "₹0.00";
  const num = Number(value);
  if (Number.isNaN(num)) return `₹${value}`;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatGrams(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "0.000 g";
  const num = Number(value);
  if (Number.isNaN(num)) return `${value} g`;
  return `${num.toFixed(3)} g`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return value;
  }
}

export const DICTIONARY: Record<Language, Record<string, string>> = {
  en: {
    tagline: "Make every gold exchange transparent, explainable, accountable and verifiable.",
    online: "Online",
    offline: "Offline",
    demoBanner: "DEMO MODE — Simulated values are clearly labelled and never represented as live instrument readings.",
    dashboard: "Dashboard",
    newExchange: "New Exchange",
    ocrImport: "OCR Scan",
    analytics: "Analytics",
    myExchanges: "My Exchanges",
    verifyQr: "Verify Passport",
    adminOps: "Platform Audit",
    signOut: "Sign Out",
    pendingSync: "Pending Sync",
    syncNow: "Sync Queue",
    totalTransactions: "Total Transactions",
    totalGoldWeight: "Net Gold Processed",
    totalExchangeValue: "Total Exchange Value",
    reviewRequired: "Review Required",
    recentTransactions: "Recent Gold Exchanges",
    scanQr: "Scan Transaction QR",
    askAssistantTitle: "GoldProof Voice & Text Assistant",
    askAssistantSubtitle: "Ask in Tamil, English, or Tanglish. Every answer comes strictly from your recorded transaction evidence.",
    tapToSpeak: "Tap Microphone to Speak",
    listening: "Listening… Speak now",
    stopListening: "Stop Listening",
    sendQuestion: "Ask",
    readAloud: "Listen",
    stopAudio: "Stop Audio",
    acknowledgeBtn: "Confirm & Acknowledge Record",
    acknowledgedBadge: "Acknowledged",
    issuePassportBtn: "Issue Signed Digital Gold Passport",
    shareReceipt: "Share / Print Receipt",
    valuationTitle: "Transparent Valuation Breakdown",
    deductionsTitle: "Itemized Deductions & Reasons",
    intelligenceTitle: "AI Deduction Intelligence",
    passportTitle: "Verifiable Digital Gold Passport",
  },
  ta: {
    tagline: "ஒவ்வொரு தங்கப் பரிமாற்றத்தையும் வெளிப்படையானதாகவும் சரிபார்க்கக்கூடியதாகவும் மாற்றுவோம்.",
    online: "இணையம் இணைந்துள்ளது",
    offline: "ஆஃப்லைன் நிலை",
    demoBanner: "செயல்விளக்க முறை (DEMO) — சோதனை அளவீடுகள் தெளிவாகக் குறிக்கப்பட்டுள்ளன.",
    dashboard: "முகப்பு",
    newExchange: "புதிய பரிவர்த்தனை",
    ocrImport: "OCR ஸ்கேன்",
    analytics: "பகுப்பாய்வு",
    myExchanges: "என் பரிவர்த்தனைகள்",
    verifyQr: "பாஸ்போர்ட் சரிபார்ப்பு",
    adminOps: "தணிக்கை",
    signOut: "வெளியேறு",
    pendingSync: "ஒத்திசைவு நிலுவை",
    syncNow: "ஒத்திசை",
    totalTransactions: "மொத்த பரிவர்த்தனைகள்",
    totalGoldWeight: "மொத்த நிகர தங்க எடை",
    totalExchangeValue: "மொத்த பரிமாற்ற மதிப்பு",
    reviewRequired: "சரிபார்ப்பு தேவை",
    recentTransactions: "சமீபத்திய தங்கப் பரிவர்த்தனைகள்",
    scanQr: "QR குறியீட்டை ஸ்கேன் செய்",
    askAssistantTitle: "GoldProof தமிழ் & ஆங்கில குரல் உதவியாளர்",
    askAssistantSubtitle: "தமிழ் அல்லது ஆங்கிலத்தில் கேளுங்கள். உங்கள் பரிவர்த்தனை ஆதாரங்களின் அடிப்படையில் மட்டுமே பதில் அளிக்கப்படும்.",
    tapToSpeak: "பேச மைக்ரோஃபோனைத் தொடவும்",
    listening: "கேட்கிறது… இப்போது பேசுங்கள்",
    stopListening: "நிறுத்து",
    sendQuestion: "கேள்",
    readAloud: "ஒலியாகக் கேள்",
    stopAudio: "ஒலியை நிறுத்து",
    acknowledgeBtn: "விவரங்களை உறுதி செய்து ஒப்புதல் அளி",
    acknowledgedBadge: "ஒப்புதல் அளிக்கப்பட்டது",
    issuePassportBtn: "Digital Gold Passport கையொப்பமிடு",
    shareReceipt: "ரசீதைப் பகிர் / அச்சிடு",
    valuationTitle: "வெளிப்படையான தங்க மதிப்புக் கணக்கீடு",
    deductionsTitle: "கழிவுகள் மற்றும் காரணங்கள்",
    intelligenceTitle: "AI கழிவு நுண்ணறிவு",
    passportTitle: "சரிபார்க்கக்கூடிய Digital Gold Passport",
  },
};

export function t(lang: Language, key: string): string {
  return DICTIONARY[lang]?.[key] ?? DICTIONARY.en[key] ?? key;
}
