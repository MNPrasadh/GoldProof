"use client";

import React, { useEffect, useRef, useState } from "react";
import { FileCheck2, Mic, MicOff, Send, Sparkles, Volume2, VolumeX } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { t } from "@/lib/i18n";
import { Language } from "@/lib/types";
import { Badge, Button, Card, Input, Skeleton } from "@/components/ui/primitives";

interface AssistantTurn {
  question: string;
  answer: string;
  language: string;
  citations: string[];
  missing_information: string[];
  provider_mode: string;
  is_external_llm: boolean;
}

const SAMPLE_QUESTIONS: { lang: Language; text: string }[] = [
  { lang: "ta", text: "எனது தங்கத்தின் மதிப்பு எவ்வளவு?" },
  { lang: "en", text: "Why was ₹3,000 deducted?" },
  { lang: "en", text: "What does 22K purity mean?" },
  { lang: "en", text: "How was my final exchange value calculated?" },
];

export function VoiceAssistantPanel({
  transactionId,
  defaultLanguage,
}: {
  transactionId: string;
  defaultLanguage?: Language;
}) {
  const { language } = useAuth();
  const [voiceLang, setVoiceLang] = useState<Language>(defaultLanguage || language || "ta");
  const [question, setQuestion] = useState("");
  const [listening, setListening] = useState(false);
  const [loading, setLoading] = useState(false);
  const [speakingIdx, setSpeakingIdx] = useState<number | null>(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [voiceNote, setVoiceNote] = useState<string | null>(null);
  const [history, setHistory] = useState<AssistantTurn[]>([]);
  const recognitionRef = useRef<{ stop: () => void } | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SR =
        (window as unknown as { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown }).SpeechRecognition ||
        (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition;
      setSpeechSupported(Boolean(SR));
    }
    return () => {
      recognitionRef.current?.stop();
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const askQuestion = async (qText: string, langOverride?: Language) => {
    const trimmed = qText.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setVoiceNote(null);
    try {
      const resp = await apiRequest<{
        transaction_id: string;
        transaction_code: string;
        language: string;
        answer: string;
        citations: string[];
        missing_information: string[];
        provider_mode: string;
        is_external_llm: boolean;
      }>("/api/assistant/ask", {
        method: "POST",
        body: JSON.stringify({
          transaction_id: transactionId,
          question: trimmed,
          language: langOverride || voiceLang,
        }),
      });
      setHistory((prev) => [
        ...prev,
        {
          question: trimmed,
          answer: resp.answer,
          language: resp.language,
          citations: resp.citations,
          missing_information: resp.missing_information,
          provider_mode: resp.provider_mode,
          is_external_llm: resp.is_external_llm,
        },
      ]);
      setQuestion("");
    } catch (err) {
      setVoiceNote(err instanceof Error ? err.message : "Could not reach assistant.");
    } finally {
      setLoading(false);
    }
  };

  const toggleMic = () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const SR =
      (window as unknown as { SpeechRecognition?: new () => any; webkitSpeechRecognition?: new () => any })
        .SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: new () => any }).webkitSpeechRecognition;

    if (!SR) {
      setVoiceNote("Browser voice recognition unavailable here. Use the Tamil/English text box or sample buttons below.");
      return;
    }

    try {
      const rec = new SR();
      rec.lang = voiceLang === "ta" ? "ta-IN" : "en-IN";
      rec.interimResults = true;
      rec.maxAlternatives = 1;

      rec.onresult = (event: { results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => {
        const lastIdx = event.results.length - 1;
        const transcript = event.results[lastIdx][0].transcript;
        setQuestion(transcript);
        if (event.results[lastIdx].isFinal) {
          setListening(false);
          askQuestion(transcript, voiceLang);
        }
      };
      rec.onerror = () => {
        setListening(false);
        setVoiceNote("Microphone could not capture speech. Please type or tap a quick question.");
      };
      rec.onend = () => setListening(false);

      recognitionRef.current = rec;
      rec.start();
      setListening(true);
      setVoiceNote(null);
    } catch {
      setListening(false);
      setVoiceNote("Unable to start microphone. Please type your question below.");
    }
  };

  const toggleSpeak = (idx: number, text: string, lang: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setVoiceNote("Audio playback is not supported on this device browser.");
      return;
    }
    if (speakingIdx === idx) {
      window.speechSynthesis.cancel();
      setSpeakingIdx(null);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === "ta" ? "ta-IN" : "en-IN";
    utterance.rate = 0.95;
    utterance.onend = () => setSpeakingIdx(null);
    utterance.onerror = () => setSpeakingIdx(null);
    setSpeakingIdx(idx);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <Card className="gold-hairline space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/10 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-[#D4AF37]" />
            <h3 className="text-base font-semibold text-[#F5F5F7]">{t(language, "askAssistantTitle")}</h3>
          </div>
          <p className="mt-1 text-xs text-[#9A9AA6]">{t(language, "askAssistantSubtitle")}</p>
        </div>

        <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-[#0B0B0D] p-1">
          <button
            type="button"
            onClick={() => setVoiceLang("ta")}
            className={`min-h-[34px] rounded-lg px-3 text-xs font-medium cursor-pointer transition-colors ${
              voiceLang === "ta" ? "bg-[#D4AF37] text-[#0B0B0D]" : "text-[#9A9AA6] hover:text-white"
            }`}
          >
            தமிழ் (ta-IN)
          </button>
          <button
            type="button"
            onClick={() => setVoiceLang("en")}
            className={`min-h-[34px] rounded-lg px-3 text-xs font-medium cursor-pointer transition-colors ${
              voiceLang === "en" ? "bg-[#D4AF37] text-[#0B0B0D]" : "text-[#9A9AA6] hover:text-white"
            }`}
          >
            English (en-IN)
          </button>
        </div>
      </div>

      {/* Prominent Voice Trigger */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <Button
          type="button"
          size="lg"
          variant={listening ? "danger" : "primary"}
          onClick={toggleMic}
          className={`sm:w-auto shrink-0 ${listening ? "voice-pulse" : ""}`}
        >
          {listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          <span>{listening ? t(language, "stopListening") : t(language, "tapToSpeak")}</span>
        </Button>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            askQuestion(question);
          }}
          className="flex flex-1 gap-2"
        >
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={
              listening
                ? t(language, "listening")
                : voiceLang === "ta"
                ? "தமிழ் அல்லது ஆங்கிலத்தில் கேளுங்கள்..."
                : "Ask about purity, rate, weight, or deductions..."
            }
          />
          <Button type="submit" variant="secondary" disabled={loading || !question.trim()}>
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">{t(language, "sendQuestion")}</span>
          </Button>
        </form>
      </div>

      {!speechSupported && (
        <p className="text-[11px] text-[#9A9AA6]">
          Text input is active (Web Speech API microphone is unavailable in this browser).
        </p>
      )}
      {voiceNote && <p className="text-xs text-amber-300">{voiceNote}</p>}

      {/* Quick Tamil & English Chips */}
      <div className="flex flex-wrap gap-2">
        {SAMPLE_QUESTIONS.map((sample) => (
          <button
            key={sample.text}
            type="button"
            onClick={() => {
              setVoiceLang(sample.lang);
              askQuestion(sample.text, sample.lang);
            }}
            className="min-h-[36px] rounded-full border border-white/12 bg-white/[0.04] px-3.5 py-1 text-xs text-[#E8D5B5] hover:border-[#D4AF37]/45 hover:bg-[#D4AF37]/12 transition-colors cursor-pointer"
          >
            {sample.text}
          </button>
        ))}
      </div>

      {loading && (
        <div className="rounded-xl border border-white/10 bg-[#0B0B0D]/75 p-4 space-y-2.5">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </div>
      )}

      {/* Conversation Evidence Cards */}
      {history.length > 0 && (
        <div className="space-y-3 pt-1">
          {history.map((turn, idx) => (
            <div
              key={idx}
              className="animate-fade-in rounded-2xl border border-white/10 bg-[#0B0B0D]/80 p-4 space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-semibold text-[#D4AF37]">“{turn.question}”</p>
                <div className="flex items-center gap-2">
                  <Badge tone="neutral">
                    {turn.is_external_llm ? turn.provider_mode : "Evidence Explainer (Local)"}
                  </Badge>
                  <button
                    type="button"
                    onClick={() => toggleSpeak(idx, turn.answer, turn.language)}
                    className="inline-flex min-h-[32px] items-center gap-1 rounded-lg border border-white/12 bg-white/[0.05] px-2.5 text-xs text-[#E8D5B5] hover:bg-white/10 cursor-pointer"
                  >
                    {speakingIdx === idx ? (
                      <>
                        <VolumeX className="h-3.5 w-3.5" />
                        {t(language, "stopAudio")}
                      </>
                    ) : (
                      <>
                        <Volume2 className="h-3.5 w-3.5" />
                        {t(language, "readAloud")}
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="whitespace-pre-line text-sm leading-relaxed text-[#F5F5F7]">{turn.answer}</div>

              {turn.citations.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-white/8">
                  <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#9A9AA6] mr-1">
                    <FileCheck2 className="h-3 w-3 text-[#D4AF37]" /> Recorded Evidence:
                  </span>
                  {turn.citations.map((c, cIdx) => (
                    <span
                      key={cIdx}
                      className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[11px] font-mono text-[#E8D5B5]"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              )}

              {turn.missing_information.length > 0 && (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                  <span className="font-semibold">Evidence gaps flagged: </span>
                  {turn.missing_information.join(" · ")}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
