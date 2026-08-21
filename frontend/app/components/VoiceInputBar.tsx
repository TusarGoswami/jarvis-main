"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Send, ScreenShare, Languages, Sparkles, ChevronUp } from "lucide-react";
import { useAssistantState } from "../hooks/useAssistantState";
import { STATE_CONFIG } from "./types";

interface VoiceInputBarProps {
  onSendQuery: (query: string, includeScreen: boolean, lang: string) => void;
  onToggleListening: () => void;
  isLoading: boolean;
}

const PRESETS = [
  { label: "🔍 Inspect Screen", query: "Analyze what is currently open on my screen", accent: "cyan" },
  { label: "⚡ System Stats", query: "Check CPU and memory usage", accent: "default" },
  { label: "📝 Launch Notepad", query: "Open Notepad and write project notes", accent: "default" },
  { label: "🎵 YouTube Music", query: "Play synthwave chill music on YouTube", accent: "default" },
  { label: "🇮🇳 हिन्दी मोड़", query: "हिंदी में बताओ आज का मौसम और समय", accent: "amber" },
  { label: "🇧🇩 বাংলা মোড", query: "আমাকে বাংলায় একটি মজার গল্প শোনাও", accent: "purple" },
];

/**
 * VoiceInputBar — Unified pill-shaped input bar at bottom center.
 *
 * Carries forward from MultimodalBar:
 *  - includeScreen toggle with context-aware placeholder
 *  - Language selector (auto/en/hi/bn)
 *  - Preset quick commands
 *  - Form submit guard (empty check + loading)
 */
export const VoiceInputBar: React.FC<VoiceInputBarProps> = ({
  onSendQuery,
  onToggleListening,
  isLoading,
}) => {
  const { state } = useAssistantState();
  const [text, setText] = useState("");
  const [includeScreen, setIncludeScreen] = useState(false);
  const [language, setLanguage] = useState("auto");
  const [showPresets, setShowPresets] = useState(false);
  const isListening = state === "listening";
  const waveCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const { audioAmplitude } = useAssistantState();
  const ampRef = useRef(audioAmplitude);

  useEffect(() => {
    ampRef.current = audioAmplitude;
  }, [audioAmplitude]);

  // Inline waveform visualization when listening
  useEffect(() => {
    if (!isListening) return;
    const canvas = waveCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let t = 0;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bars = 20;
      const barWidth = canvas.width / bars;
      const amp = ampRef.current;

      for (let i = 0; i < bars; i++) {
        const h = (Math.sin(t * 4 + i * 0.5) * 0.3 + 0.4 + amp * 0.5) * canvas.height * 0.8;
        const x = i * barWidth + barWidth * 0.15;
        const y = (canvas.height - h) / 2;
        ctx.fillStyle = `rgba(239, 68, 68, ${0.5 + amp * 0.5})`;
        ctx.fillRect(x, y, barWidth * 0.7, h);
      }
      t += 0.016;
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(animId);
  }, [isListening]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSendQuery(text, includeScreen, language);
    setText("");
  };

  const handlePreset = (query: string) => {
    onSendQuery(query, includeScreen, language);
    setShowPresets(false);
  };

  const cfg = STATE_CONFIG[state];

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 w-full max-w-2xl px-4">
      {/* Presets dropdown */}
      <AnimatePresence>
        {showPresets && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="flex flex-wrap gap-2 justify-center pb-1"
          >
            {PRESETS.map((p) => (
              <button
                key={p.query}
                onClick={() => handlePreset(p.query)}
                className={`px-3 py-1.5 rounded-full text-xs font-mono transition-all hover:scale-105 ${
                  p.accent === "cyan"
                    ? "bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-900/60"
                    : p.accent === "amber"
                    ? "bg-amber-950/50 border border-amber-500/30 text-amber-300 hover:bg-amber-900/50"
                    : p.accent === "purple"
                    ? "bg-purple-950/50 border border-purple-500/30 text-purple-300 hover:bg-purple-900/50"
                    : "bg-slate-900/80 border border-slate-700 text-gray-300 hover:bg-slate-800"
                }`}
              >
                {p.label}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main pill bar */}
      <motion.form
        onSubmit={handleSubmit}
        className="w-full glass-panel-glow rounded-2xl p-1.5 flex items-center gap-1.5"
        animate={{
          borderColor: `rgba(${cfg.glowRgb}, 0.4)`,
          boxShadow: `0 0 25px rgba(${cfg.glowRgb}, 0.15), 0 4px 20px rgba(0,0,0,0.4)`,
        }}
        transition={{ type: "spring", stiffness: 100, damping: 15 }}
      >
        {/* Presets toggle */}
        <button
          type="button"
          onClick={() => setShowPresets(!showPresets)}
          className="p-2.5 rounded-xl bg-slate-900/80 text-gray-400 hover:text-cyan-300 transition border border-slate-800 flex-shrink-0"
          title="Quick commands"
        >
          <ChevronUp
            className={`w-4 h-4 transition-transform ${showPresets ? "rotate-180" : ""}`}
          />
        </button>

        {/* Screen toggle - carries forward includeScreen from MultimodalBar */}
        <button
          type="button"
          onClick={() => setIncludeScreen(!includeScreen)}
          title="Include active screen snapshot in query context"
          className={`p-2.5 rounded-xl transition flex items-center gap-1 text-xs font-mono flex-shrink-0 ${
            includeScreen
              ? "bg-cyan-500 text-black font-bold shadow-[0_0_15px_rgba(0,240,255,0.6)]"
              : "bg-slate-900/80 text-gray-400 hover:text-cyan-300 border border-slate-800"
          }`}
        >
          <ScreenShare className="w-4 h-4" />
        </button>

        {/* Language selector - carries forward from MultimodalBar */}
        <div className="relative flex items-center flex-shrink-0">
          <Languages className="w-3.5 h-3.5 absolute left-2 text-cyan-400/60 pointer-events-none" />
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="pl-7 pr-2 py-2 bg-slate-950/80 border border-slate-800 rounded-xl text-xs font-mono text-gray-300 focus:outline-none focus:border-cyan-500/40"
          >
            <option value="auto">Auto</option>
            <option value="en">EN</option>
            <option value="hi">हि</option>
            <option value="bn">বা</option>
          </select>
        </div>

        {/* Text input - carries forward context-aware placeholder from MultimodalBar */}
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            isListening
              ? "Listening..."
              : includeScreen
              ? "Ask about your screen..."
              : "Ask Vocalis AI anything..."
          }
          disabled={isListening}
          className="flex-1 bg-transparent px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none min-w-0"
        />

        {/* Inline waveform when listening */}
        <AnimatePresence>
          {isListening && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 80, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
              className="overflow-hidden flex-shrink-0"
            >
              <canvas
                ref={waveCanvasRef}
                width={80}
                height={32}
                className="rounded"
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Mic button */}
        <motion.button
          type="button"
          onClick={onToggleListening}
          disabled={state === "thinking" || state === "speaking"}
          className={`p-3 rounded-xl transition flex items-center justify-center flex-shrink-0 ${
            isListening
              ? "bg-red-500 text-white shadow-[0_0_20px_rgba(239,68,68,0.8)]"
              : "bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-900/80"
          }`}
          animate={
            isListening
              ? { scale: [1, 1.08, 1] }
              : state === "idle"
              ? { boxShadow: ["0 0 10px rgba(0,240,255,0.2)", "0 0 20px rgba(0,240,255,0.4)", "0 0 10px rgba(0,240,255,0.2)"] }
              : {}
          }
          transition={
            isListening
              ? { duration: 1, repeat: Infinity, ease: "easeInOut" }
              : { duration: 2.5, repeat: Infinity, ease: "easeInOut" }
          }
        >
          {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
        </motion.button>

        {/* Send button */}
        <button
          type="submit"
          disabled={isLoading || !text.trim()}
          className="p-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-black font-bold hover:brightness-110 disabled:opacity-30 transition shadow-[0_0_15px_rgba(0,240,255,0.3)] flex-shrink-0"
        >
          <Send className="w-4 h-4" />
        </button>
      </motion.form>
    </div>
  );
};
