"use client";
/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars */

import React, { useState, useEffect, useRef, useMemo } from "react";
import { motion } from "framer-motion";

// Components
import { ParticleBackground } from "./components/ParticleBackground";
import { AssistantAvatar } from "./components/AssistantAvatar";
import { StateRing } from "./components/StateRing";
import { VoiceInputBar } from "./components/VoiceInputBar";
import { ActivityDrawer } from "./components/ActivityDrawer";
import { TelemetryStrip } from "./components/TelemetryStrip";
import { DevStateToggle } from "./components/DevStateToggle";
import { EvalBenchmarkModal } from "./components/EvalBenchmarkModal";

// Hooks & Types
import { AssistantContext } from "./hooks/useAssistantState";
import type { AssistantState, MessageItem, SystemStats } from "./components/types";

export default function VocalisHome() {
  // ─── Core State ───
  const [rawState, setRawState] = useState<AssistantState>("idle");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [audioMuted, setAudioMuted] = useState(false);
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

  // ─── Track unread messages when drawer is closed ───
  const prevMessageCount = useRef(0);
  useEffect(() => {
    if (messages.length > prevMessageCount.current && !isDrawerOpen) {
      const newCount = messages.length - prevMessageCount.current;
      setUnreadCount((c) => c + newCount);
    }
    prevMessageCount.current = messages.length;
  }, [messages.length, isDrawerOpen]);

  // Clear unread when drawer opens
  useEffect(() => {
    if (isDrawerOpen) setUnreadCount(0);
  }, [isDrawerOpen]);

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
              // Map "processing" to "thinking" in the new 5-state system
              if (data.state === "processing") setRawState("thinking");
            } else if (data.type === "turn_result") {
              const res = data.data;
              setRawState(data.audio_base64 && !audioMuted ? "speaking" : "idle");

              const newMsg: MessageItem = {
                id: Date.now().toString(),
                sender: "vocalis",
                text: res.reply_text,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                language: res.language,
                confidence: res.confidence,
                intent: res.intent,
                actionsExecuted: res.actions_executed,
                needsConfirmation: res.needs_confirmation,
                confirmationReason: res.confirmation_reason,
                citations: res.citations,
                latencyMs: res.latency_ms,
              };

              setMessages((prev) => [...prev, newMsg]);

              // Play audio if provided and not muted
              if (data.audio_base64 && !audioMuted) {
                const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`);
                audio.onended = () => setRawState("idle");
                audio.play().catch(() => setRawState("idle"));
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

    // Fetch initial system telemetry via REST (preserved from original)
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
      if (wsRef.current) wsRef.current.close();
    };
  }, [audioMuted]);

  // ─── Voice Speech Recognition (preserved from original) ───
  const toggleListening = () => {
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
    const userMsg: MessageItem = {
      id: Date.now().toString(),
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
        })
      );
    } else {
      // Fallback REST endpoint (preserved from original)
      try {
        const res = await fetch("http://127.0.0.1:8005/api/agent/command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query,
            language: lang === "auto" ? undefined : lang,
            allow_actions: true,
          }),
        });
        const resData = await res.json();
        setRawState("idle");

        const vocalisMsg: MessageItem = {
          id: (Date.now() + 1).toString(),
          sender: "vocalis",
          text: resData.reply_text,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          language: resData.language,
          confidence: resData.confidence,
          intent: resData.intent,
          actionsExecuted: resData.actions_executed,
          needsConfirmation: resData.needs_confirmation,
          confirmationReason: resData.confirmation_reason,
          citations: resData.citations,
          latencyMs: resData.latency_ms,
        };
        setMessages((prev) => [...prev, vocalisMsg]);
      } catch (err) {
        setRawState("idle");
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
        setRawState("speaking");
        audio.onended = () => setRawState("idle");
        audio.play().catch(() => setRawState("idle"));
      }
    } catch {
      setRawState("idle");
    }
  };

  // ─── "Spotlight" behavior: dim side elements when not idle ───
  const isActive = effectiveState !== "idle";

  return (
    <AssistantContext.Provider value={contextValue}>
      <main className="min-h-screen bg-[#030712] text-gray-100 relative overflow-hidden">
        {/* Animated particle background */}
        <ParticleBackground />

        {/* Telemetry strip (thin top bar) */}
        <TelemetryStrip
          stats={stats}
          isConnected={isWsConnected}
          audioMuted={audioMuted}
          onToggleMute={() => setAudioMuted(!audioMuted)}
          onOpenEvals={() => setIsEvalOpen(true)}
        />

        {/* ─── Central Avatar Stage ─── */}
        <div className="relative z-10 flex flex-col items-center justify-center min-h-screen pt-12 pb-28">
          {/* Avatar + Ring container */}
          <motion.div
            className="relative flex items-center justify-center"
            style={{
              width: "clamp(340px, 45vw, 520px)",
              height: "clamp(340px, 45vw, 520px)",
            }}
            animate={{
              scale: isActive ? 1.02 : 1,
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

          {/* Subtle ambient text */}
          <motion.p
            className="mt-6 text-gray-500 text-sm font-mono tracking-wide text-center"
            animate={{
              opacity: isActive ? 0.3 : 0.7,
            }}
            transition={{ duration: 0.5 }}
          >
            {effectiveState === "idle" && "Say something or type a command..."}
            {effectiveState === "listening" && "I'm listening..."}
            {effectiveState === "thinking" && "Processing your request..."}
            {effectiveState === "speaking" && ""}
            {effectiveState === "tool_use" && "Executing actions..."}
          </motion.p>
        </div>

        {/* Voice input bar (fixed bottom center) */}
        <VoiceInputBar
          onSendQuery={handleSendQuery}
          onToggleListening={toggleListening}
          isLoading={effectiveState === "thinking"}
        />

        {/* Activity drawer (slide-in from right) */}
        <ActivityDrawer
          isOpen={isDrawerOpen}
          onToggle={() => setIsDrawerOpen(!isDrawerOpen)}
          messages={messages}
          onConfirmAction={handleConfirmAction}
          onCancelAction={handleCancelAction}
          onPlayAudio={handlePlayAudio}
          unreadCount={unreadCount}
        />

        {/* Dev state toggle (bottom-left, for testing) */}
        <DevStateToggle />

        {/* Eval benchmark modal (preserved from original) */}
        <EvalBenchmarkModal isOpen={isEvalOpen} onClose={() => setIsEvalOpen(false)} />
      </main>
    </AssistantContext.Provider>
  );
}
