"use client";
/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars */

import React, { useState, useEffect, useRef } from "react";
import { ArcReactor } from "./components/ArcReactor";
import { TelemetryPanel, SystemStats } from "./components/TelemetryPanel";
import { MultimodalBar } from "./components/MultimodalBar";
import { ActionFeed, MessageItem } from "./components/ActionFeed";
import { WorkspaceExplorer } from "./components/WorkspaceExplorer";
import { EvalBenchmarkModal } from "./components/EvalBenchmarkModal";
import { Terminal, Shield, Activity, Award, Volume2, VolumeX, Folder } from "lucide-react";

export default function VocalisHome() {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [state, setState] = useState<"idle" | "listening" | "processing" | "speaking">("idle");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isEvalOpen, setIsEvalOpen] = useState(false);
  const [audioMuted, setAudioMuted] = useState(false);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [currentAgentSteps, setCurrentAgentSteps] = useState<any[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<any>(null);

  // Initialize WebSocket connection to FastAPI backend
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
              if (data.state === "processing") setState("processing");
            } else if (data.type === "step_update") {
              setCurrentAgentSteps((prev) => {
                const idx = prev.findIndex((s) => s.step === data.step.step);
                if (idx > -1) {
                  const updated = [...prev];
                  updated[idx] = data.step;
                  return updated;
                } else {
                  return [...prev, data.step];
                }
              });
            } else if (data.type === "turn_result") {
              const res = data.data;
              setState(data.audio_base64 && !audioMuted ? "speaking" : "idle");
              setCurrentAgentSteps([]);

              const newMsg: MessageItem = {
                id: Date.now().toString(),
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
                audio.onended = () => setState("idle");
                audio.play().catch(() => setState("idle"));
              } else {
                setState("idle");
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
        // Fallback default stats
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 5000);

    return () => {
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [audioMuted]);

  // Voice speech recognition setup
  const toggleListening = () => {
    if (state === "listening") {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setState("idle");
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
      setState("listening");
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setState("idle");
      handleSendQuery(transcript, false, "auto");
    };

    recognition.onerror = () => {
      setState("idle");
    };

    recognition.onend = () => {
      setState("idle");
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const handleSendQuery = async (query: string, includeScreen: boolean, lang: string) => {
    setCurrentAgentSteps([]);
    const userMsg: MessageItem = {
      id: Date.now().toString(),
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setState("processing");

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
      // Fallback REST endpoint
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
        setState("idle");

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
        setState("idle");
        console.error(err);
      }
    }
  };

  const handleConfirmAction = async (messageId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, needsConfirmation: false } : m))
    );
    // Execute authorized action
    handleSendQuery("Execute authorized action", false, "en");
  };

  const handleCancelAction = (messageId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, needsConfirmation: false } : m))
    );
  };

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
        setState("speaking");
        audio.onended = () => setState("idle");
        audio.play().catch(() => setState("idle"));
      }
    } catch {
      setState("idle");
    }
  };

  return (
    <main className="min-h-screen bg-[#030712] text-gray-100 flex flex-col scanline relative">
      {/* Top Futuristic Header */}
      <header className="border-b border-cyan-500/20 bg-slate-950/80 backdrop-blur-md px-6 py-3.5 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-400/40 flex items-center justify-center shadow-[0_0_15px_rgba(0,240,255,0.4)]">
            <Terminal className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-black font-mono tracking-wider text-cyan-300">
                VOCALIS AI
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 font-semibold">
                v2.0.0 MULTIMODAL OS
              </span>
            </div>
            <p className="text-[11px] text-gray-400 font-mono">
              Hybrid Vision + Voice Autonomous Intelligence Engine
            </p>
          </div>
        </div>

        {/* Right header controls */}
        <div className="flex items-center gap-3 font-mono text-xs">
          <button
            onClick={() => setIsEvalOpen(true)}
            className="px-3 py-1.5 rounded-xl bg-cyan-950 border border-cyan-500/40 text-cyan-300 hover:bg-cyan-900/50 flex items-center gap-1.5 transition shadow-[0_0_15px_rgba(0,240,255,0.2)]"
          >
            <Award className="w-4 h-4 text-cyan-400" />
            <span>Eval Harness (30 Tests)</span>
          </button>

          <button
            onClick={() => setAudioMuted(!audioMuted)}
            title="Toggle TTS audio voice feedback"
            className={`p-2 rounded-xl border transition ${
              audioMuted
                ? "bg-slate-900 border-slate-700 text-gray-500"
                : "bg-cyan-950 border-cyan-500/40 text-cyan-300"
            }`}
          >
            {audioMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-[11px]">
            <span
              className={`w-2 h-2 rounded-full ${
                isWsConnected ? "bg-emerald-400 animate-pulse" : "bg-red-400"
              }`}
            />
            <span className="text-gray-300">{isWsConnected ? "WS STREAM ACTIVE" : "OFFLINE / REST"}</span>
          </div>
        </div>
      </header>

      {/* Main Grid Layout */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Telemetry & Workspace Artifacts (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-5">
          <TelemetryPanel stats={stats} />
          <WorkspaceExplorer />

          <div className="glass-panel p-4 rounded-2xl flex flex-col gap-2.5 font-mono text-xs">
            <span className="text-gray-400 uppercase text-[10px] tracking-wider flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-cyan-400" /> Core Capabilities
            </span>
            <div className="flex flex-col gap-1 text-[11px] text-gray-300">
              <div className="flex items-center justify-between py-1 border-b border-slate-800">
                <span>Autonomous ReAct</span>
                <strong className="text-emerald-400">Active (Multi-Tool)</strong>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800">
                <span>Sandboxed File &amp; Shell</span>
                <strong className="text-cyan-400">./workspace</strong>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800">
                <span>Multi-Lingual STT/TTS</span>
                <strong className="text-emerald-400">EN, HI, BN</strong>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800">
                <span>Vision Screen Analysis</span>
                <strong className="text-cyan-400">Gemini 2.5 Flash</strong>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800">
                <span>Safety Guardrails</span>
                <strong className="text-cyan-400">Active (70% Gate)</strong>
              </div>
              <div className="flex items-center justify-between py-1">
                <span>Backend Framework</span>
                <strong className="text-cyan-400">FastAPI + UV</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Center/Right Column: Arc Reactor Core, Action Feed & Multimodal Bar (8 cols) */}
        <div className="lg:col-span-8 flex flex-col gap-5">
          {/* Arc Reactor Centerpiece */}
          <div className="glass-panel p-6 rounded-2xl flex flex-col items-center justify-center relative overflow-hidden">
            <ArcReactor state={state} />
          </div>

          {/* Action and Conversation Feed */}
          <div className="glass-panel p-5 rounded-2xl flex flex-col min-h-[340px]">
            <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3 mb-3">
              <span className="font-mono text-xs uppercase tracking-widest text-cyan-400 flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400 animate-pulse" /> Agentic Activity Stream
              </span>
              <span className="text-[10px] font-mono text-gray-400">
                Confidence &amp; Safety Guardrails Enabled
              </span>
            </div>
            <ActionFeed
              messages={messages}
              onConfirmAction={handleConfirmAction}
              onCancelAction={handleCancelAction}
              onPlayAudio={handlePlayAudio}
            />

            {state === "processing" && currentAgentSteps.length > 0 && (
              <div className="mt-4 p-3 bg-cyan-950/20 border border-cyan-500/20 rounded-xl font-mono text-[11px] text-cyan-300 animate-pulse">
                <div className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                  Execution Steps In Progress:
                </div>
                <div className="space-y-1.5 border-l border-cyan-800/80 pl-3">
                  {currentAgentSteps.map((st, idx) => (
                    <div key={idx} className="flex flex-col gap-0.5">
                      <div className="text-gray-300 italic">💭 {st.thought}</div>
                      {st.action && (
                        <div className="text-cyan-400 font-bold flex items-center gap-1">
                          ⚡ Tool: {st.action} ({st.status})
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Multimodal Input Bar */}
          <MultimodalBar
            onSendQuery={handleSendQuery}
            isListening={state === "listening"}
            onToggleListening={toggleListening}
            isLoading={state === "processing"}
          />
        </div>
      </div>

      {/* Eval Benchmark Modal for Hackathon Judges */}
      <EvalBenchmarkModal isOpen={isEvalOpen} onClose={() => setIsEvalOpen(false)} />
    </main>
  );
}
