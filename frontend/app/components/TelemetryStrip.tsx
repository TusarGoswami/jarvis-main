"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  ChevronUp,
  Cpu,
  HardDrive,
  Wifi,
  Battery,
  Award,
  Volume2,
  VolumeX,
  Bot,
  UserCheck,
  Square,
  Zap,
  MessageSquare,
  Check,
} from "lucide-react";
import type { SystemStats } from "./types";

export type AppMode = "action" | "chat" | "interview" | "jarvis";

interface TelemetryStripProps {
  stats: SystemStats | null;
  isConnected: boolean;
  audioMuted: boolean;
  onToggleMute: () => void;
  onOpenEvals: () => void;
  appMode: AppMode;
  onModeChange: (mode: AppMode) => void;
  isSpeaking?: boolean;
  isTalkingStopped?: boolean;
  onStopTalking?: () => void;
  maxTokens?: number;
  onMaxTokensChange?: (tokens: number) => void;
}

/**
 * TelemetryStrip — Collapsible thin top bar for system stats with mode switching.
 * Supports [ACTION], [CHAT], and [INTERVIEW] protocol mode toggles.
 */
export const TelemetryStrip: React.FC<TelemetryStripProps> = ({
  stats,
  isConnected,
  audioMuted,
  onToggleMute,
  onOpenEvals,
  appMode,
  onModeChange,
  isSpeaking,
  isTalkingStopped,
  onStopTalking,
  maxTokens,
  onMaxTokensChange,
}) => {
  const [expanded, setExpanded] = useState(false);

  // Fallback defaults carried from TelemetryPanel
  const cpu = stats?.cpu_percent ?? 12.4;
  const ram = stats?.ram_percent ?? 45.2;
  const ramUsed = stats?.ram_used_gb ?? 7.2;
  const ramTotal = stats?.ram_total_gb ?? 16.0;
  const netSent = stats?.net_sent_mb ?? 142.5;
  const netRecv = stats?.net_recv_mb ?? 620.1;
  const battery = stats?.battery ?? null;

  // CPU color threshold logic
  const cpuColor = cpu > 80 ? "text-red-400" : cpu > 50 ? "text-amber-400" : "text-cyan-300";

  const isActionActive = appMode === "action" || appMode === "jarvis";
  const isChatActive = appMode === "chat";
  const isInterviewActive = appMode === "interview";

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 z-20 backdrop-blur-xl"
      style={{
        background: "rgba(3, 7, 18, 0.88)",
        borderBottom: "1px solid rgba(0, 240, 255, 0.15)",
      }}
      layout
    >
      {/* Collapsed strip — always visible */}
      <div className="flex items-center justify-between px-4 py-1.5 text-xs font-mono">
        {/* Left: Brand & Mode Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="text-cyan-300 font-black tracking-wider text-[11px]">
              VOCALIS AI
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30 text-cyan-400/80">
              v2.0.0
            </span>
          </div>

          {/* 3-Mode Switcher Buttons */}
          <div className="flex items-center bg-slate-950 p-0.5 rounded-xl border border-cyan-500/30">
            {/* ACTION MODE */}
            <button
              onClick={() => onModeChange("action")}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-wider transition-all flex items-center gap-1.5 ${
                isActionActive
                  ? "bg-cyan-500/20 border border-cyan-400/60 text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.35)]"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              title="Action Mode: Assign and execute autonomous tasks & tools"
            >
              <Zap className="w-3 h-3 text-cyan-400" />
              <span>ACTION</span>
            </button>

            {/* CHAT MODE */}
            <button
              onClick={() => onModeChange("chat")}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-wider transition-all flex items-center gap-1.5 ${
                isChatActive
                  ? "bg-purple-500/20 border border-purple-400/60 text-purple-300 shadow-[0_0_12px_rgba(168,85,247,0.35)]"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              title="Chat Mode: Voice & text conversational interface"
            >
              <MessageSquare className="w-3 h-3 text-purple-400" />
              <span>CHAT</span>
            </button>

            {/* INTERVIEW MODE */}
            <button
              onClick={() => onModeChange("interview")}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-wider transition-all flex items-center gap-1.5 ${
                isInterviewActive
                  ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-400/60 text-cyan-300 shadow-[0_0_12px_rgba(0,240,255,0.35)]"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              title="Interview Mode: Technical mock interview protocol"
            >
              <UserCheck className="w-3 h-3 text-cyan-400" />
              <span>INTERVIEW</span>
            </button>
          </div>
        </div>

        {/* Center: Quick stats */}
        <div className="hidden md:flex items-center gap-4 text-[11px]">
          <span className="flex items-center gap-1 text-gray-400">
            <Cpu className="w-3 h-3 text-cyan-400/60" />
            <span className={cpuColor}>{cpu.toFixed(0)}%</span>
          </span>
          <span className="flex items-center gap-1 text-gray-400">
            <HardDrive className="w-3 h-3 text-emerald-400/60" />
            <span className="text-emerald-300">{ram.toFixed(0)}%</span>
          </span>
          <span className="flex items-center gap-1 text-gray-400">
            <Wifi className="w-3 h-3 text-cyan-400/60" />
            <span className="text-gray-300">↑{netSent.toFixed(0)} ↓{netRecv.toFixed(0)}</span>
          </span>
          {battery !== null && (
            <span className="flex items-center gap-1 text-gray-400">
              <Battery className="w-3 h-3 text-amber-400/60" />
              <span className="text-amber-300">{battery}%</span>
            </span>
          )}
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-2">
          {/* Stop Talking Button when speaking */}
          {isSpeaking && onStopTalking && (
            <button
              onClick={onStopTalking}
              className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-red-600 text-white font-bold animate-pulse hover:bg-red-500 transition text-[10px] shadow-[0_0_10px_rgba(239,68,68,0.7)] cursor-pointer"
              title="Stop audio playback"
            >
              <Square className="w-3 h-3 fill-white" />
              <span>STOP TALKING</span>
            </button>
          )}

          {/* Talking Stopped Feedback */}
          {isTalkingStopped && (
            <div
              className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/90 border border-emerald-500/50 text-emerald-300 font-bold text-[10px] shadow-[0_0_10px_rgba(16,185,129,0.5)]"
            >
              <Check className="w-3 h-3 text-emerald-400" />
              <span>STOPPED</span>
            </div>
          )}

          {/* Token Limit Indicator */}
          {maxTokens && (
            <div className="hidden lg:flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900/80 border border-slate-800 text-[10px] text-cyan-300/90" title="Token Limit Size">
              <span>{maxTokens} tk</span>
            </div>
          )}

          {/* WS status */}
          <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900/80 border border-slate-800 text-[10px]">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isConnected ? "bg-emerald-400 animate-pulse" : "bg-red-400"
              }`}
            />
            <span className="text-gray-400">{isConnected ? "LIVE" : "OFF"}</span>
          </div>

          {/* Mute toggle */}
          <button
            onClick={onToggleMute}
            title="Toggle TTS audio"
            className={`p-1 rounded transition ${
              audioMuted ? "text-gray-500" : "text-cyan-300"
            }`}
          >
            {audioMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          </button>

          {/* Eval button */}
          <button
            onClick={onOpenEvals}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/30 text-cyan-300/80 hover:text-cyan-200 transition text-[10px]"
          >
            <Award className="w-3 h-3" />
            <span className="hidden sm:inline">Evals</span>
          </button>

          {/* Expand/collapse toggle */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 rounded text-gray-400 hover:text-cyan-300 transition"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Expanded detail view */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="overflow-hidden border-t border-cyan-500/10"
          >
            <div className="px-4 py-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
              {/* CPU detail */}
              <div className="flex flex-col gap-1">
                <span className="text-gray-400 text-[10px]">CPU LOAD</span>
                <div className="w-full bg-slate-900/80 rounded-full h-1.5 overflow-hidden border border-slate-700/50">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${
                      cpu > 80 ? "bg-red-500" : cpu > 50 ? "bg-amber-400" : "bg-cyan-400"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(5, cpu))}%` }}
                  />
                </div>
                <span className={cpuColor}>{cpu.toFixed(1)}%</span>
              </div>

              {/* RAM detail */}
              <div className="flex flex-col gap-1">
                <span className="text-gray-400 text-[10px]">RAM MEMORY</span>
                <div className="w-full bg-slate-900/80 rounded-full h-1.5 overflow-hidden border border-slate-700/50">
                  <div
                    className="h-full bg-emerald-400 transition-all duration-500 rounded-full"
                    style={{ width: `${Math.min(100, Math.max(5, ram))}%` }}
                  />
                </div>
                <span className="text-emerald-300">{ramUsed}/{ramTotal} GB</span>
              </div>

              {/* Network detail */}
              <div className="flex flex-col gap-1">
                <span className="text-gray-400 text-[10px]">NETWORK</span>
                <div className="flex gap-2 text-[11px]">
                  <span className="text-cyan-300">↑ {netSent.toFixed(1)} MB</span>
                  <span className="text-emerald-300">↓ {netRecv.toFixed(1)} MB</span>
                </div>
              </div>

              {/* Disks */}
              {stats?.disks && Object.keys(stats.disks).length > 0 && (
                <div className="flex flex-col gap-1">
                  <span className="text-gray-400 text-[10px]">STORAGE</span>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(stats.disks).map(([drive, pct]) => (
                      <span
                        key={drive}
                        className="text-[10px] px-1.5 py-0.5 bg-slate-900 rounded border border-slate-700 text-gray-300"
                      >
                        {drive}: <strong className="text-cyan-400">{pct}%</strong>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
