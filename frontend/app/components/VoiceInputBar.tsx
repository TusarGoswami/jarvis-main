"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Send, ScreenShare, Languages, ChevronUp, Square, Check, Zap, MessageSquare } from "lucide-react";
import { useAssistantState } from "../hooks/useAssistantState";
import { STATE_CONFIG } from "./types";
import type { AppMode } from "./TelemetryStrip";

interface VoiceInputBarProps {
  onSendQuery: (query: string, includeScreen: boolean, lang: string, imageBase64?: string) => void;
  onToggleListening: () => void;
  isLoading: boolean;
  onStopTalking?: () => void;
  isTalkingStopped?: boolean;
  maxTokens?: number;
  onMaxTokensChange?: (tokens: number) => void;
  appMode?: AppMode;
  onModeChange?: (mode: AppMode) => void;
}

const PRESETS = [
  { label: "🔍 Inspect Screen", query: "Analyze what is currently open on my screen", accent: "cyan" },
  { label: "⚡ System Stats", query: "Check CPU and memory usage", accent: "default" },
  { label: "📝 Launch Notepad", query: "Open Notepad and write project notes", accent: "default" },
  { label: "📧 Send Email", query: "Send an email to team@company.com saying project updates are ready", accent: "cyan" },
  { label: "🎵 YouTube Music", query: "Play synthwave chill music on YouTube", accent: "default" },
  { label: "🇮🇳 हिन्दी मोड़", query: "हिंदी में बताओ आज का मौसम और समय", accent: "amber" },
  { label: "🇧🇩 বাংলা মোড", query: "আমাকে বাংলায় একটি মজার গল্প শোনাও", accent: "purple" },
];

/**
 * VoiceInputBar — Unified pill-shaped input bar at bottom center.
 */
export const VoiceInputBar: React.FC<VoiceInputBarProps> = ({
  onSendQuery,
  onToggleListening,
  isLoading,
  onStopTalking,
  isTalkingStopped,
  maxTokens,
  onMaxTokensChange,
  appMode,
  onModeChange,
}) => {
  const { state } = useAssistantState();
  const [text, setText] = useState("");
  const [includeScreen, setIncludeScreen] = useState(false);
  const [screenImage, setScreenImage] = useState<string | null>(null);
  const [isCapturingScreen, setIsCapturingScreen] = useState(false);
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

  const handleScreenToggle = async () => {
    if (includeScreen) {
      setIncludeScreen(false);
      setScreenImage(null);
      return;
    }

    setIsCapturingScreen(true);
    try {
      if (typeof window !== "undefined" && navigator?.mediaDevices?.getDisplayMedia) {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: { cursor: "always" } as any,
          audio: false,
        });

        const video = document.createElement("video");
        video.srcObject = stream;
        await video.play();

        const canvas = document.createElement("canvas");
        canvas.width = Math.min(video.videoWidth || 1280, 1280);
        canvas.height = (canvas.width * (video.videoHeight || 720)) / (video.videoWidth || 1280);
        const ctx = canvas.getContext("2d");
        ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

        // Stop screen tracks
        stream.getTracks().forEach((track) => track.stop());

        setScreenImage(dataUrl);
        setIncludeScreen(true);

        if (!text.trim()) {
          setText("Analyze and explain what is visible on my screen.");
        }
      } else {
        setIncludeScreen(true);
        if (!text.trim()) {
          setText("Analyze what is currently open on my screen.");
        }
      }
    } catch {
      // User cancelled dialog or permission denied: fallback to includeScreen=true (backend capture)
      setIncludeScreen(true);
      if (!text.trim()) {
        setText("Analyze what is currently open on my screen.");
      }
    } finally {
      setIsCapturingScreen(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const queryToSend = text.trim() || (includeScreen ? "Analyze what is visible on my screen right now." : "");
    if (!queryToSend || isLoading) return;
    onSendQuery(queryToSend, includeScreen, language, screenImage || undefined);
    setText("");
    setIncludeScreen(false);
    setScreenImage(null);
  };

  const handlePreset = (query: string) => {
    onSendQuery(query, includeScreen, language, screenImage || undefined);
    setShowPresets(false);
    setIncludeScreen(false);
    setScreenImage(null);
  };

  const cfg = STATE_CONFIG[state];

  const isChat = appMode === "chat";

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 w-full max-w-2xl px-4">
      {/* Screen Snapshot Preview Pill */}
      <AnimatePresence>
        {includeScreen && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-950/90 border border-cyan-400/50 shadow-[0_0_20px_rgba(0,240,255,0.25)] text-cyan-200 text-xs font-mono"
          >
            {screenImage ? (
              <img
                src={screenImage}
                alt="Screen preview"
                className="w-8 h-5 object-cover rounded border border-cyan-500/40"
              />
            ) : (
              <ScreenShare className="w-4 h-4 text-cyan-400 animate-pulse" />
            )}
            <span className="font-semibold">🖥️ Active Screen Attached</span>
            <span className="text-[10px] text-cyan-400/70 hidden sm:inline">| Ready for Vision Analysis</span>
            <button
              type="button"
              onClick={() => {
                setIncludeScreen(false);
                setScreenImage(null);
              }}
              className="ml-1 text-slate-400 hover:text-red-400 cursor-pointer font-bold px-1"
              title="Remove screen attachment"
            >
              ✕
            </button>
          </motion.div>
        )}
      </AnimatePresence>

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
        {/* Dedicated Action Mode / Chat Mode Toggle Button */}
        {onModeChange && (
          <button
            type="button"
            onClick={() => onModeChange(isChat ? "action" : "chat")}
            className={`p-2 px-2.5 rounded-xl font-mono text-xs font-bold transition-all flex items-center gap-1.5 flex-shrink-0 cursor-pointer ${
              isChat
                ? "bg-purple-950/80 border border-purple-500/50 text-purple-300 hover:bg-purple-900/80 shadow-[0_0_12px_rgba(168,85,247,0.35)]"
                : "bg-cyan-950/80 border border-cyan-500/50 text-cyan-300 hover:bg-cyan-900/80 shadow-[0_0_12px_rgba(0,240,255,0.35)]"
            }`}
            title={isChat ? "Currently in Chat Mode. Click to switch to Action Mode" : "Currently in Action Mode. Click to switch to Chat Mode"}
          >
            {isChat ? (
              <>
                <MessageSquare className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-[11px] tracking-wider hidden sm:inline">CHAT</span>
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5 text-cyan-400" />
                <span className="text-[11px] tracking-wider hidden sm:inline">ACTION</span>
              </>
            )}
          </button>
        )}

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

        {/* Screen toggle */}
        <button
          type="button"
          onClick={handleScreenToggle}
          disabled={isCapturingScreen}
          title={includeScreen ? "Active screen attached. Click to remove." : "Attach and ask about your screen"}
          className={`p-2.5 rounded-xl transition flex items-center gap-1 text-xs font-mono flex-shrink-0 cursor-pointer ${
            includeScreen
              ? "bg-cyan-500 text-black font-bold shadow-[0_0_15px_rgba(0,240,255,0.6)]"
              : "bg-slate-900/80 text-gray-400 hover:text-cyan-300 border border-slate-800"
          }`}
        >
          <ScreenShare className={`w-4 h-4 ${isCapturingScreen ? "animate-spin" : ""}`} />
        </button>

        {/* Language selector */}
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

        {/* Token limit size selector */}
        {onMaxTokensChange && (
          <div className="relative flex items-center flex-shrink-0" title="Max output token limit size">
            <select
              value={maxTokens ?? 150}
              onChange={(e) => onMaxTokensChange(Number(e.target.value))}
              className="px-2 py-2 bg-slate-950/80 border border-slate-800 rounded-xl text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500/40"
            >
              <option value={75}>75 tk</option>
              <option value={150}>150 tk</option>
              <option value={250}>250 tk</option>
              <option value={500}>500 tk</option>
            </select>
          </div>
        )}

        {/* Text input */}
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            isListening
              ? "Listening..."
              : includeScreen
              ? "Ask about your screen..."
              : isChat
              ? "Chat with Vocalis AI..."
              : "Command actions (e.g. send email, open app, calendar, search)..."
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

        {/* Stop Talking Button / Talking Stopped feedback */}
        <AnimatePresence>
          {state === "speaking" && onStopTalking && (
            <motion.button
              type="button"
              onClick={onStopTalking}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="p-2.5 px-3 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 text-white font-bold hover:brightness-110 transition shadow-[0_0_15px_rgba(239,68,68,0.8)] flex items-center gap-1.5 flex-shrink-0 text-xs font-mono cursor-pointer"
              title="Stop Talking"
            >
              <Square className="w-3.5 h-3.5 fill-white" />
              <span>Stop</span>
            </motion.button>
          )}

          {isTalkingStopped && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="p-2 px-2.5 rounded-xl bg-emerald-950/90 border border-emerald-500/50 text-emerald-300 font-bold flex items-center gap-1 flex-shrink-0 text-xs font-mono shadow-[0_0_12px_rgba(16,185,129,0.5)]"
            >
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="hidden sm:inline">Stopped</span>
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
