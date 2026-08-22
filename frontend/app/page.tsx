"use client";
/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars */

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Square, Check } from "lucide-react";

// Components
import { ParticleBackground } from "./components/ParticleBackground";
import { AssistantAvatar } from "./components/AssistantAvatar";
import { StateRing } from "./components/StateRing";
import { VoiceInputBar } from "./components/VoiceInputBar";
import { ActivityDrawer } from "./components/ActivityDrawer";
import { TelemetryStrip, AppMode } from "./components/TelemetryStrip";
import { DevStateToggle } from "./components/DevStateToggle";
import { EvalBenchmarkModal } from "./components/EvalBenchmarkModal";
import { InterviewProtocol } from "./components/interview/InterviewProtocol";
import { ChatMode } from "./components/ChatMode";

// Hooks & Types
import { AssistantStateProvider } from "./hooks/useAssistantState";
import type { AssistantState, MessageItem, SystemStats } from "./components/types";

export default function VocalisHome() {
  // ─── Mode State (ACTION vs CHAT vs INTERVIEW) ───
  const [appMode, setAppMode] = useState<AppMode>("action");

  // ─── Core State ───
  const [rawState, setRawState] = useState<AssistantState>("idle");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [currentAgentSteps, setCurrentAgentSteps] = useState<any[]>([]);
  const [audioMuted, setAudioMuted] = useState(false);
  const [maxTokens, setMaxTokens] = useState<number>(150);
  const [isTalkingStopped, setIsTalkingStopped] = useState(false);
  const [isEvalOpen, setIsEvalOpen] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // ─── Dev Override State ───
  const [devOverride, setDevOverride] = useState<AssistantState | null>(null);
  const [devAmplitude, setDevAmplitude] = useState(0);
  const [liveAmplitude, setLiveAmplitude] = useState(0);

  // Effective state (dev override takes priority)
  const effectiveState = devOverride ?? rawState;
  const effectiveAmplitude = devOverride !== null ? devAmplitude : liveAmplitude;

  // ─── Refs ───
  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<any>(null);
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  const currentTurnIdRef = useRef<number>(0);

  // ─── Central Audio Interrupt & Sequence Manager ───
  const stopCurrentAudio = useCallback(() => {
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current.currentTime = 0;
      activeAudioRef.current = null;
    }
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setRawState("idle");
    setIsTalkingStopped(true);
    setTimeout(() => {
      setIsTalkingStopped(false);
    }, 1800);
  }, []);

  // ─── Context value (memoized for performance) ───
  const contextValue = useMemo(
    () => ({
      state: effectiveState,
      audioAmplitude: effectiveAmplitude,
      transcript: "",
      isConnected: isWsConnected,
      devOverride,
      setDevOverride,
      setDevAmplitude,
    }),
    [effectiveState, effectiveAmplitude, isWsConnected, devOverride]
  );

  const handleDrawerToggle = () => {
    setIsDrawerOpen((prev) => {
      const next = !prev;
      if (next) setUnreadCount(0);
      return next;
    });
  };

  // ─── WebSocket Connection (preserved from original) ───
  useEffect(() => {
    let ws: WebSocket;
    const connect = () => {
      try {
        ws = new WebSocket("ws://127.0.0.1:8005/ws/stream");
        wsRef.current = ws;

        ws.onopen = () => {
          setIsWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "handshake" || data.type === "pong") {
              if (data.stats) setStats(data.stats);
            } else if (data.type === "status") {
              if (data.state === "processing") setRawState("thinking");
              if (data.state === "tool_use") setRawState("tool_use");
            } else if (data.type === "turn_result") {
              // If turn_id exists and doesn't match the current turn, discard stale answer
              if (data.turn_id && data.turn_id !== currentTurnIdRef.current) {
                return;
              }

              const res = data.data;
              stopCurrentAudio();

              const newMsg: MessageItem = {
                id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
                sender: "vocalis",
                text: res.reply_text,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                language: res.language,
                confidence: res.confidence,
                intent: res.intent,
                actionsExecuted: res.actions_executed,
                steps: res.steps,
                needsConfirmation: res.needs_confirmation,
                confirmationReason: res.confirmation_reason,
                citations: res.citations,
                latencyMs: res.latency_ms,
              };

              setMessages((prev) => [...prev, newMsg]);

              // Play audio if provided and not muted
              if (data.audio_base64 && !audioMuted) {
                const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`);
                activeAudioRef.current = audio;
                setRawState("speaking");
                audio.onended = () => {
                  if (activeAudioRef.current === audio) {
                    activeAudioRef.current = null;
                    setRawState("idle");
                  }
                };
                audio.play().catch(() => {
                  if (activeAudioRef.current === audio) {
                    activeAudioRef.current = null;
                    setRawState("idle");
                  }
                });
              } else {
                setRawState("idle");
              }
            }
          } catch (err) {
            console.error("Error parsing WS message:", err);
          }
        };

        ws.onclose = () => {
          setIsWsConnected(false);
          setTimeout(connect, 3000); // Auto reconnect
        };
      } catch (e) {
        setIsWsConnected(false);
      }
    };

    connect();

    // Fetch initial system telemetry via REST
    const fetchStats = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8005/api/system/stats");
        if (res.ok) {
          const json = await res.json();
          setStats(json.data);
        }
      } catch {
        // Fallback default stats handled by TelemetryStrip
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 5000);

    return () => {
      clearInterval(interval);
      stopCurrentAudio();
      if (wsRef.current) wsRef.current.close();
    };
  }, [audioMuted, stopCurrentAudio]);

  // ─── Voice Speech Recognition (preserved from original) ───
  const toggleListening = () => {
    stopCurrentAudio();
    if (rawState === "listening") {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setRawState("idle");
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please type your query.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setRawState("listening");
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setRawState("idle");
      handleSendQuery(transcript, false, "auto");
    };

    recognition.onerror = () => {
      setRawState("idle");
    };

    recognition.onend = () => {
      setRawState("idle");
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  // ─── Query Handling (preserved from original) ───
  const handleSendQuery = async (query: string, includeScreen: boolean, lang: string) => {
    // 1. Immediately cancel any currently playing or scheduled audio
    stopCurrentAudio();

    // 2. Increment turn ID to invalidate any prior pending responses
    const turnId = ++currentTurnIdRef.current;

    setCurrentAgentSteps([]);
    const userMsg: MessageItem = {
      id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setRawState("thinking");

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "query",
          query: query,
          include_screen: includeScreen,
          language: lang === "auto" ? undefined : lang,
          turn_id: turnId,
          max_tokens: maxTokens,
        })
      );
    } else {
      // Fallback REST endpoint
      try {
        const res = await fetch("http://127.0.0.1:8005/api/agent/command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query,
            language: lang === "auto" ? undefined : lang,
            allow_actions: true,
            max_tokens: maxTokens,
          }),
        });
        const resData = await res.json();
        
        // If user asked another question while this request was in flight, discard it
        if (turnId !== currentTurnIdRef.current) return;
        setRawState("idle");

        const vocalisMsg: MessageItem = {
          id: `vocalis-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          sender: "vocalis",
          text: resData.reply_text,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          language: resData.language,
          confidence: resData.confidence,
          intent: resData.intent,
          actionsExecuted: resData.actions_executed,
          steps: resData.steps,
          needsConfirmation: resData.needs_confirmation,
          confirmationReason: resData.confirmation_reason,
          citations: resData.citations,
          latencyMs: resData.latency_ms,
        };
        setMessages((prev) => [...prev, vocalisMsg]);
      } catch (err) {
        if (turnId === currentTurnIdRef.current) {
          setRawState("idle");
        }
        console.error(err);
      }
    }
  };

  // ─── Action Confirmation (preserved from original) ───
  const handleConfirmAction = async (messageId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, needsConfirmation: false } : m))
    );
    handleSendQuery("Execute authorized action", false, "en");
  };

  const handleCancelAction = (messageId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, needsConfirmation: false } : m))
    );
  };

  // ─── TTS Audio Playback (preserved from original) ───
  const handlePlayAudio = async (text: string, lang?: string) => {
    stopCurrentAudio();
    try {
      const res = await fetch("http://127.0.0.1:8005/api/agent/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, language: lang || "en" }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        activeAudioRef.current = audio;
        setRawState("speaking");
        audio.onended = () => {
          if (activeAudioRef.current === audio) {
            activeAudioRef.current = null;
            setRawState("idle");
          }
        };
        audio.play().catch(() => {
          if (activeAudioRef.current === audio) {
            activeAudioRef.current = null;
            setRawState("idle");
          }
        });
      }
    } catch {
      setRawState("idle");
    }
  };

  // ─── "Spotlight" behavior: dim side elements when active ───
  const isActive = effectiveState !== "idle";

  return (
    <AssistantStateProvider value={contextValue}>
      <main className="min-h-screen bg-[#030712] text-gray-100 relative overflow-x-hidden flex flex-col justify-between">
        {/* Animated particle background */}
        <ParticleBackground />

        {/* Telemetry strip (thin top bar with ACTION / CHAT / INTERVIEW mode switch) */}
        <TelemetryStrip
          stats={stats}
          isConnected={isWsConnected}
          audioMuted={audioMuted}
          onToggleMute={() => setAudioMuted(!audioMuted)}
          onOpenEvals={() => setIsEvalOpen(true)}
          appMode={appMode}
          onModeChange={setAppMode}
          isSpeaking={effectiveState === "speaking"}
          isTalkingStopped={isTalkingStopped}
          onStopTalking={stopCurrentAudio}
          maxTokens={maxTokens}
          onMaxTokensChange={setMaxTokens}
        />

        {/* ─── Mode Switching Content ─── */}
        <AnimatePresence mode="wait">
          {appMode === "interview" ? (
            /* ─── INTERVIEW MODE (Technical Interview Protocol) ─── */
            <motion.div
              key="interview-mode"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.25 }}
              className="flex-1 pt-12 pb-16"
            >
              <InterviewProtocol />
            </motion.div>
          ) : appMode === "chat" ? (
            /* ─── CHAT MODE (Interactive Voice & Text Conversation) ─── */
            <motion.div
              key="chat-mode"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col"
            >
              <ChatMode
                messages={messages}
                onSendQuery={handleSendQuery}
                onToggleListening={toggleListening}
                onConfirmAction={handleConfirmAction}
                onCancelAction={handleCancelAction}
                onPlayAudio={handlePlayAudio}
                onStopTalking={stopCurrentAudio}
                isSpeaking={effectiveState === "speaking"}
                isTalkingStopped={isTalkingStopped}
                maxTokens={maxTokens}
                onMaxTokensChange={setMaxTokens}
                isLoading={effectiveState === "thinking" || effectiveState === "tool_use"}
                onClearChat={() => setMessages([])}
                appMode={appMode}
                onModeChange={setAppMode}
              />
            </motion.div>
          ) : (
            /* ─── ACTION MODE (Clean Autonomous Avatar Core & Voice Input) ─── */
            <motion.div
              key="action-mode"
              initial={{ opacity: 0, y: -15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 15 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col justify-between"
            >
              {/* Central Avatar Stage (Dominant Central Viewport) */}
              <div className="relative z-10 flex-1 flex flex-col items-center justify-center pt-16 pb-28 px-4">
                {/* Avatar + Ring container */}
                <motion.div
                  className="relative flex items-center justify-center"
                  style={{
                    width: "clamp(320px, 42vw, 500px)",
                    height: "clamp(320px, 42vw, 500px)",
                  }}
                  animate={{
                    scale: isActive ? 1.03 : 1,
                  }}
                  transition={{ type: "spring", stiffness: 100, damping: 20 }}
                >
                  {/* State ring behind avatar */}
                  <StateRing />

                  {/* Robot avatar centered inside ring */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <AssistantAvatar />
                  </div>
                </motion.div>

                {/* Ambient state text */}
                <motion.p
                  className="mt-6 text-gray-400 text-sm font-mono tracking-wide text-center"
                  animate={{
                    opacity: isActive ? 0.4 : 0.8,
                  }}
                  transition={{ duration: 0.5 }}
                >
                  {effectiveState === "idle" && "Speak or type actions (e.g. send email, calendar, launch app)..."}
                  {effectiveState === "listening" && "Listening to your voice..."}
                  {effectiveState === "thinking" && "Reasoning & executing plan..."}
                  {effectiveState === "speaking" && "Responding..."}
                  {effectiveState === "tool_use" && "Autonomous tool execution active..."}
                </motion.p>

                {/* Stop Talking Button / Talking Stopped Feedback when speaking */}
                <AnimatePresence>
                  {effectiveState === "speaking" && (
                    <motion.button
                      initial={{ opacity: 0, scale: 0.8, y: 10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.8, y: 10 }}
                      onClick={stopCurrentAudio}
                      className="mt-4 px-6 py-2 rounded-full bg-gradient-to-r from-red-600 via-rose-600 to-purple-600 text-white font-mono font-bold text-xs shadow-[0_0_25px_rgba(239,68,68,0.7)] hover:scale-105 transition-all flex items-center gap-2 border border-red-400/50 cursor-pointer z-30 tracking-wider"
                      title="Stop audio playback"
                    >
                      <Square className="w-4 h-4 fill-white" />
                      <span>STOP TALKING</span>
                    </motion.button>
                  )}

                  {isTalkingStopped && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8, y: 10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.8, y: 10 }}
                      className="mt-4 px-6 py-2 rounded-full bg-emerald-950/90 border border-emerald-500/60 text-emerald-300 font-mono font-bold text-xs shadow-[0_0_20px_rgba(16,185,129,0.6)] flex items-center gap-2 z-30 tracking-wider"
                    >
                      <Check className="w-4 h-4 text-emerald-400" />
                      <span>TALKING STOPPED</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Voice input bar (fixed bottom center) */}
              <VoiceInputBar
                onSendQuery={handleSendQuery}
                onToggleListening={toggleListening}
                isLoading={effectiveState === "thinking" || effectiveState === "tool_use"}
                onStopTalking={stopCurrentAudio}
                isTalkingStopped={isTalkingStopped}
                maxTokens={maxTokens}
                onMaxTokensChange={setMaxTokens}
                appMode={appMode}
                onModeChange={setAppMode}
              />

              {/* Activity & Workspace drawer (slide-in from right) */}
              <ActivityDrawer
                isOpen={isDrawerOpen}
                onToggle={handleDrawerToggle}
                messages={messages}
                onConfirmAction={handleConfirmAction}
                onCancelAction={handleCancelAction}
                onPlayAudio={handlePlayAudio}
                unreadCount={unreadCount}
              />

              {/* Dev state toggle (bottom-left, for interactive testing) */}
              <DevStateToggle />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Eval benchmark modal */}
        <EvalBenchmarkModal isOpen={isEvalOpen} onClose={() => setIsEvalOpen(false)} />
      </main>
    </AssistantStateProvider>
  );
}
