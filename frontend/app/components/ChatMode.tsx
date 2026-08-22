"use client";

import React, { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Sparkles,
  Bot,
  User,
  Volume2,
  Square,
  Check,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  Cpu,
  Trash2
} from "lucide-react";
import type { MessageItem } from "./types";
import { VoiceInputBar } from "./VoiceInputBar";
import type { AppMode } from "./TelemetryStrip";

interface ChatModeProps {
  messages: MessageItem[];
  onSendQuery: (query: string, includeScreen: boolean, lang: string) => void;
  onToggleListening: () => void;
  onConfirmAction: (messageId: string) => void;
  onCancelAction: (messageId: string) => void;
  onPlayAudio?: (text: string, lang?: string) => void;
  onStopTalking?: () => void;
  isSpeaking: boolean;
  isTalkingStopped: boolean;
  maxTokens: number;
  onMaxTokensChange: (tokens: number) => void;
  isLoading: boolean;
  onClearChat?: () => void;
  appMode?: AppMode;
  onModeChange?: (mode: AppMode) => void;
}

const CHAT_PROMPTS = [
  "👋 Hello Vocalis, who are you?",
  "📧 Draft an email to team@company.com",
  "🔍 What are the latest trends in autonomous agents?",
  "⚡ Check my current system telemetry and CPU load",
];

export const ChatMode: React.FC<ChatModeProps> = ({
  messages,
  onSendQuery,
  onToggleListening,
  onConfirmAction,
  onCancelAction,
  onPlayAudio,
  onStopTalking,
  isSpeaking,
  isTalkingStopped,
  maxTokens,
  onMaxTokensChange,
  isLoading,
  onClearChat,
  appMode,
  onModeChange,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeStepTab, setActiveStepTab] = useState<Record<string, boolean>>({});

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, isLoading]);

  const toggleStepView = (msgId: string) => {
    setActiveStepTab((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div className="flex-1 flex flex-col justify-between max-w-4xl w-full mx-auto px-4 pt-16 pb-24 h-[calc(100vh-4rem)]">
      {/* Chat Header */}
      <div className="flex items-center justify-between py-2 border-b border-cyan-500/20 mb-3 text-xs font-mono">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-300">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-gray-100">Vocalis Conversational Chat</span>
            <span className="text-gray-500 ml-2">({messages.length} messages)</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Stop Talking Button */}
          {isSpeaking && onStopTalking && (
            <motion.button
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              onClick={onStopTalking}
              className="px-3 py-1 rounded-full bg-gradient-to-r from-red-600 to-rose-600 text-white font-bold flex items-center gap-1.5 shadow-[0_0_15px_rgba(239,68,68,0.7)] hover:brightness-110 transition text-[11px]"
            >
              <Square className="w-3.5 h-3.5 fill-white" />
              <span>STOP TALKING</span>
            </motion.button>
          )}

          {/* Talking Stopped Feedback */}
          {isTalkingStopped && (
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 font-bold flex items-center gap-1 text-[11px] shadow-[0_0_12px_rgba(16,185,129,0.5)]"
            >
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>TALKING STOPPED</span>
            </motion.div>
          )}

          {/* Clear chat button */}
          {messages.length > 0 && onClearChat && (
            <button
              onClick={onClearChat}
              className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-950/40 transition"
              title="Clear conversation"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Message Stream */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto pr-2 space-y-4 scroll-smooth"
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
            <div className="w-16 h-16 rounded-full bg-cyan-950/60 border border-cyan-500/40 flex items-center justify-center text-cyan-300 shadow-[0_0_30px_rgba(0,240,255,0.2)]">
              <Bot className="w-8 h-8 animate-pulse" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-100 mb-1">
                Chat & Communicate with Vocalis AI
              </h2>
              <p className="text-xs text-gray-400 font-mono max-w-md">
                Ask questions, converse naturally, or command tasks. Vocalis responds with concise voice and multimodal intelligence.
              </p>
            </div>

            {/* Quick Prompts */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 max-w-lg w-full">
              {CHAT_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => onSendQuery(p.replace(/^[^\s]+\s/, ""), false, "auto")}
                  className="p-2.5 rounded-xl glass-panel text-left text-xs text-gray-300 hover:text-cyan-300 hover:border-cyan-500/40 transition font-mono border border-slate-800"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex items-start gap-3 ${
                msg.sender === "user" ? "flex-row-reverse" : "flex-row"
              }`}
            >
              {/* Avatar Icon */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold font-mono border ${
                  msg.sender === "user"
                    ? "bg-blue-950/80 border-blue-500/40 text-blue-300 shadow-[0_0_10px_rgba(59,130,246,0.3)]"
                    : "bg-cyan-950/80 border-cyan-500/40 text-cyan-300 shadow-[0_0_10px_rgba(0,240,255,0.3)]"
                }`}
              >
                {msg.sender === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Content */}
              <div
                className={`max-w-[82%] rounded-2xl p-4 text-sm leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-gradient-to-r from-blue-950/70 to-indigo-950/70 border border-blue-500/40 text-gray-100 rounded-tr-none shadow-[0_4px_20px_rgba(0,0,0,0.4)]"
                    : "glass-panel text-gray-100 border border-cyan-500/20 rounded-tl-none shadow-[0_4px_20px_rgba(0,0,0,0.5)]"
                }`}
              >
                {/* Header info */}
                <div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b border-white/5 text-[10px] font-mono text-gray-400">
                  <span className={msg.sender === "vocalis" ? "text-cyan-400 font-bold" : "text-blue-400 font-bold"}>
                    {msg.sender === "vocalis" ? "VOCALIS AI" : "YOU"}
                  </span>
                  <div className="flex items-center gap-2">
                    {msg.latencyMs && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300">
                        {msg.latencyMs}ms
                      </span>
                    )}
                    <span>{msg.timestamp}</span>
                  </div>
                </div>

                {/* Body Text */}
                <div className="flex items-start justify-between gap-3">
                  <p className="whitespace-pre-wrap font-sans text-sm text-gray-200">{msg.text}</p>
                  {msg.sender === "vocalis" && onPlayAudio && (
                    <button
                      onClick={() => onPlayAudio(msg.text, msg.language)}
                      title="Play Voice Audio"
                      className="p-1.5 rounded-lg hover:bg-cyan-500/20 text-cyan-400 transition flex-shrink-0"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Badges (Confidence, Intent, Citations) */}
                {msg.sender === "vocalis" && (
                  <div className="mt-3 pt-2 border-t border-cyan-900/30 flex flex-wrap items-center gap-2 text-[10px] font-mono">
                    {msg.confidence !== undefined && (
                      <span
                        className={`px-2 py-0.5 rounded-full flex items-center gap-1 border ${
                          msg.confidence >= 0.85
                            ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                            : "bg-amber-950/60 border-amber-500/40 text-amber-300"
                        }`}
                      >
                        <ShieldCheck className="w-3 h-3" />
                        {Math.round(msg.confidence * 100)}% Conf
                      </span>
                    )}

                    {msg.intent && (
                      <span className="px-2 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-gray-300">
                        Intent: {msg.intent}
                      </span>
                    )}

                    {msg.citations && msg.citations.length > 0 && (
                      <span className="px-2 py-0.5 rounded-full bg-blue-950/60 border border-blue-500/40 text-blue-300">
                        Grounding: {msg.citations.join(", ")}
                      </span>
                    )}
                  </div>
                )}

                {/* Multi-Step ReAct Plan & Reasoning Trace */}
                {msg.steps && msg.steps.length > 0 && (
                  <div className="mt-3 bg-black/60 p-3 rounded-xl border border-cyan-500/20 flex flex-col gap-2 text-xs font-mono">
                    <button
                      onClick={() => toggleStepView(msg.id)}
                      className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider flex items-center justify-between hover:text-cyan-200 transition"
                    >
                      <span className="flex items-center gap-1">
                        <Sparkles className="w-3 h-3 text-cyan-400" /> Multi-Step Agent Plan ({msg.steps.length} steps)
                      </span>
                      <span>{activeStepTab[msg.id] ? "Collapse ▲" : "View Steps ▼"}</span>
                    </button>

                    {activeStepTab[msg.id] && (
                      <div className="space-y-2 border-l border-cyan-900/60 pl-3 ml-1 mt-1">
                        {msg.steps.map((st, i) => (
                          <div key={i} className="flex flex-col gap-1 text-[11px]">
                            <div className="text-white/80 italic font-sans">
                              💭 {st.thought}
                            </div>
                            {st.action && (
                              <div className="flex items-center gap-2 text-cyan-300">
                                <span className="px-1.5 py-0.5 rounded bg-cyan-950/80 border border-cyan-800 text-[10px] text-cyan-200">
                                  ⚡ Tool: {st.action}
                                </span>
                                {st.status === "completed" && (
                                  <span className="text-emerald-400 flex items-center gap-1 text-[10px]">
                                    <CheckCircle2 className="w-3 h-3" /> Verified
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Actions Executed Summary */}
                {msg.actionsExecuted && msg.actionsExecuted.length > 0 && (
                  <div className="mt-2.5 bg-slate-950/80 p-2 rounded-xl border border-cyan-900/50 flex flex-col gap-1 text-xs font-mono">
                    <span className="text-[10px] text-gray-400 flex items-center gap-1">
                      <Cpu className="w-3 h-3 text-cyan-400" /> Executed System Actions:
                    </span>
                    {msg.actionsExecuted.map((act, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-cyan-300">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{act.action}: <strong>{act.target || act.query || act.command || act.message || "Success"}</strong></span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Guardrails Confirmation Gate */}
                {msg.needsConfirmation && (
                  <div className="mt-3 p-3 rounded-xl bg-amber-950/60 border border-amber-500/50 flex flex-col gap-2">
                    <div className="flex items-center gap-1.5 text-amber-300 text-xs font-bold font-mono">
                      <ShieldAlert className="w-4 h-4 text-amber-400" />
                      Human Authorization Required
                    </div>
                    <p className="text-xs text-amber-200/90">{msg.confirmationReason}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <button
                        onClick={() => onConfirmAction(msg.id)}
                        className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold font-mono rounded-lg transition shadow-[0_0_10px_rgba(245,158,11,0.4)]"
                      >
                        Authorize & Send
                      </button>
                      <button
                        onClick={() => onCancelAction(msg.id)}
                        className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-gray-300 text-xs font-mono rounded-lg transition"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3"
          >
            <div className="w-8 h-8 rounded-xl bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 flex items-center justify-center">
              <Bot className="w-4 h-4 animate-spin-slow" />
            </div>
            <div className="glass-panel p-3 rounded-2xl text-xs font-mono text-cyan-300 flex items-center gap-2">
              <Sparkles className="w-4 h-4 animate-pulse text-cyan-400" />
              <span>Vocalis AI reasoning & generating response...</span>
            </div>
          </motion.div>
        )}
      </div>

      {/* Integrated Voice & Text Input Bar */}
      <div className="w-full pt-2">
        <VoiceInputBar
          onSendQuery={onSendQuery}
          onToggleListening={onToggleListening}
          isLoading={isLoading}
          onStopTalking={onStopTalking}
          isTalkingStopped={isTalkingStopped}
          maxTokens={maxTokens}
          onMaxTokensChange={onMaxTokensChange}
          appMode={appMode}
          onModeChange={onModeChange}
        />
      </div>
    </div>
  );
};
