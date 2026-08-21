"use client";

import React from "react";
import { CheckCircle2, ShieldCheck, ShieldAlert, Cpu, Sparkles, Volume2 } from "lucide-react";
import type { MessageItem } from "./types";

// Re-export for backward compatibility
export type { MessageItem };

interface ActionFeedProps {
  messages: MessageItem[];
  onConfirmAction: (messageId: string) => void;
  onCancelAction: (messageId: string) => void;
  onPlayAudio?: (text: string, lang?: string) => void;
}

export const ActionFeed: React.FC<ActionFeedProps> = ({
  messages,
  onConfirmAction,
  onCancelAction,
  onPlayAudio,
}) => {
  return (
    <div className="flex-1 overflow-y-auto pr-2 flex flex-col gap-4">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500 font-mono text-xs gap-2">
          <Sparkles className="w-8 h-8 text-cyan-500/40 animate-pulse" />
          <span>Vocalis AI Neural Core Ready</span>
          <span className="text-[10px] text-gray-600">Speak or type a command to initialize interactive session.</span>
        </div>
      ) : (
        messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col gap-1.5 ${
              msg.sender === "user" ? "items-end" : "items-start"
            }`}
          >
            {/* Sender tag & time */}
            <div className="flex items-center gap-2 text-[10px] font-mono text-gray-400 px-1">
              <span className={msg.sender === "vocalis" ? "text-cyan-400 font-bold" : "text-emerald-400 font-bold"}>
                {msg.sender === "vocalis" ? "VOCALIS AI" : "USER"}
              </span>
              <span>•</span>
              <span>{msg.timestamp}</span>
              {msg.latencyMs && (
                <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-300">
                  {msg.latencyMs}ms
                </span>
              )}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed ${
                msg.sender === "user"
                  ? "bg-gradient-to-r from-blue-900/60 to-cyan-900/60 border border-cyan-500/30 text-white"
                  : "glass-panel text-gray-100 border-cyan-500/20 shadow-[0_4px_20px_rgba(0,0,0,0.5)]"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <p className="whitespace-pre-wrap">{msg.text}</p>
                {msg.sender === "vocalis" && onPlayAudio && (
                  <button
                    onClick={() => onPlayAudio(msg.text, msg.language)}
                    title="Speak text aloud"
                    className="p-1 rounded hover:bg-cyan-500/20 text-cyan-400 transition flex-shrink-0"
                  >
                    <Volume2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Confidence and Intent Badges */}
              {msg.sender === "vocalis" && (
                <div className="mt-3 pt-2 border-t border-cyan-900/40 flex flex-wrap items-center gap-2 text-[11px] font-mono">
                  {msg.confidence !== undefined && (
                    <span
                      className={`px-2 py-0.5 rounded-full flex items-center gap-1 border ${
                        msg.confidence >= 0.85
                          ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                          : "bg-amber-950/60 border-amber-500/40 text-amber-300"
                      }`}
                    >
                      <ShieldCheck className="w-3 h-3" />
                      {Math.round(msg.confidence * 100)}% Confidence
                    </span>
                  )}

                  {msg.intent && (
                    <span className="px-2 py-0.5 rounded-full bg-slate-900 border border-slate-700 text-gray-300">
                      Intent: {msg.intent}
                    </span>
                  )}

                  {msg.citations && msg.citations.length > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-blue-950/60 border border-blue-500/40 text-blue-300">
                      Grounded: {msg.citations.join(", ")}
                    </span>
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
                      <span>{act.action}: <strong>{act.target || act.query || "Done"}</strong></span>
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
                      className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold font-mono rounded-lg transition"
                    >
                      Authorize Action
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
          </div>
        ))
      )}
    </div>
  );
};
