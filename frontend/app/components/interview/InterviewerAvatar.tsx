"use client";

import React from "react";
import { motion } from "framer-motion";
import { UserCheck, Sparkles, Volume2, Mic, Brain, CheckCircle2 } from "lucide-react";
import type { AssistantState } from "../types";

interface InterviewerAvatarProps {
  state?: AssistantState;
}

const AVATAR_STATE_MAP = {
  idle: {
    color: "#00f0ff",
    ringBorder: "border-cyan-500/30",
    dashedBorder: "border-cyan-400/40",
    centerBorder: "border-cyan-500/50",
    shadow: "shadow-[0_0_35px_rgba(0,240,255,0.25)]",
    sweepGlow: "shadow-[0_0_10px_#00f0ff]",
    sweepGradient: "from-transparent via-cyan-400 to-transparent",
    label: "NEURAL INTERVIEW AGENT v2.0",
    badgeBg: "bg-cyan-950/80 border-cyan-500/30 text-cyan-300",
    icon: UserCheck,
    statusText: "READY",
  },
  speaking: {
    color: "#a855f7",
    ringBorder: "border-purple-500/50",
    dashedBorder: "border-purple-400/60",
    centerBorder: "border-purple-500/70",
    shadow: "shadow-[0_0_45px_rgba(168,85,247,0.45)]",
    sweepGlow: "shadow-[0_0_15px_#a855f7]",
    sweepGradient: "from-transparent via-purple-400 to-transparent",
    label: "DELIVERING QUESTION (AUDIO)",
    badgeBg: "bg-purple-950/80 border-purple-500/50 text-purple-300",
    icon: Volume2,
    statusText: "SPEAKING",
  },
  listening: {
    color: "#10b981",
    ringBorder: "border-emerald-500/50",
    dashedBorder: "border-emerald-400/60",
    centerBorder: "border-emerald-500/70",
    shadow: "shadow-[0_0_45px_rgba(16,185,129,0.45)]",
    sweepGlow: "shadow-[0_0_15px_#10b981]",
    sweepGradient: "from-transparent via-emerald-400 to-transparent",
    label: "LISTENING TO CANDIDATE",
    badgeBg: "bg-emerald-950/80 border-emerald-500/50 text-emerald-300",
    icon: Mic,
    statusText: "LISTENING",
  },
  thinking: {
    color: "#f59e0b",
    ringBorder: "border-amber-500/50",
    dashedBorder: "border-amber-400/60",
    centerBorder: "border-amber-500/70",
    shadow: "shadow-[0_0_45px_rgba(245,158,11,0.45)]",
    sweepGlow: "shadow-[0_0_15px_#f59e0b]",
    sweepGradient: "from-transparent via-amber-400 to-transparent",
    label: "EVALUATING & ADAPTING",
    badgeBg: "bg-amber-950/80 border-amber-500/50 text-amber-300",
    icon: Brain,
    statusText: "THINKING",
  },
  tool_use: {
    color: "#06b6d4",
    ringBorder: "border-cyan-500/50",
    dashedBorder: "border-cyan-400/60",
    centerBorder: "border-cyan-500/70",
    shadow: "shadow-[0_0_45px_rgba(6,182,212,0.45)]",
    sweepGlow: "shadow-[0_0_15px_#06b6d4]",
    sweepGradient: "from-transparent via-cyan-400 to-transparent",
    label: "PROCESSING BENCHMARK",
    badgeBg: "bg-cyan-950/80 border-cyan-500/50 text-cyan-300",
    icon: CheckCircle2,
    statusText: "EXECUTING",
  },
};

export const InterviewerAvatar: React.FC<InterviewerAvatarProps> = ({ state = "idle" }) => {
  const currentConfig = AVATAR_STATE_MAP[state] || AVATAR_STATE_MAP.idle;
  const StateIcon = currentConfig.icon;

  return (
    <div className="relative flex flex-col items-center justify-center">
      {/* Outer ambient biometric scanner ring */}
      <motion.div
        className={`absolute rounded-full pointer-events-none border ${currentConfig.ringBorder}`}
        style={{
          width: "180px",
          height: "180px",
        }}
        animate={{
          scale: state === "speaking" ? [1, 1.15, 1] : state === "listening" ? [1, 1.1, 1] : [1, 1.06, 1],
          opacity: state === "speaking" || state === "listening" ? [0.4, 0.9, 0.4] : [0.3, 0.6, 0.3],
          rotate: 360,
        }}
        transition={{
          scale: { duration: state === "speaking" ? 1.5 : 3, repeat: Infinity, ease: "easeInOut" },
          opacity: { duration: state === "speaking" ? 1.5 : 3, repeat: Infinity, ease: "easeInOut" },
          rotate: { duration: state === "thinking" ? 12 : 28, repeat: Infinity, ease: "linear" },
        }}
      />

      {/* Counter-rotating dashed aura */}
      <motion.div
        className={`absolute rounded-full pointer-events-none border border-dashed ${currentConfig.dashedBorder}`}
        style={{
          width: "160px",
          height: "160px",
        }}
        animate={{
          rotate: -360,
          scale: state === "speaking" ? [1, 1.05, 1] : 1,
        }}
        transition={{
          rotate: {
            duration: state === "thinking" ? 8 : 18,
            repeat: Infinity,
            ease: "linear",
          },
          scale: {
            duration: 1.2,
            repeat: Infinity,
            ease: "easeInOut",
          }
        }}
      />

      {/* Main Avatar Centerpiece */}
      <motion.div
        className={`relative w-32 h-32 rounded-2xl bg-gradient-to-b from-slate-900 via-slate-950 to-slate-900 border ${currentConfig.centerBorder} ${currentConfig.shadow} flex flex-col items-center justify-center overflow-hidden backdrop-blur-xl transition-all duration-500`}
        whileHover={{ scale: 1.03 }}
        transition={{ type: "spring", stiffness: 200, damping: 20 }}
      >
        {/* Holographic grid overlay */}
        <div className="absolute inset-0 bg-[radial-gradient(#00f0ff_1px,transparent_1px)] [background-size:12px_12px] opacity-20 pointer-events-none" />

        {/* Generative Persona Silhouette / Hologram */}
        <div className="relative z-10 flex flex-col items-center justify-center">
          <motion.div
            animate={{
              scale: state === "speaking" ? [1, 1.12, 1] : state === "listening" ? [1, 1.08, 1] : 1,
            }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
            className="w-14 h-14 rounded-full bg-slate-950/80 border flex items-center justify-center shadow-md transition-colors duration-500"
            style={{ borderColor: currentConfig.color }}
          >
            <StateIcon className="w-7 h-7 transition-colors duration-500" style={{ color: currentConfig.color }} />
          </motion.div>

          <div className="mt-2 flex items-center gap-1 text-[10px] font-mono font-bold tracking-widest uppercase" style={{ color: currentConfig.color }}>
            <Sparkles className="w-2.5 h-2.5 animate-pulse" />
            <span>VOCALIS EVALUATOR</span>
          </div>
        </div>

        {/* Scanning telemetry sweep line */}
        <motion.div
          className={`absolute left-0 right-0 h-0.5 bg-gradient-to-r ${currentConfig.sweepGradient} ${currentConfig.sweepGlow}`}
          animate={{
            top: ["0%", "100%", "0%"],
          }}
          transition={{
            duration: state === "speaking" || state === "listening" ? 2.0 : 3.5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </motion.div>

      {/* Sub-badge: Reactive state badge */}
      <div className={`mt-3 flex items-center gap-2 px-3 py-1 rounded-full border text-[10px] font-mono transition-all duration-300 ${currentConfig.badgeBg}`}>
        <span
          className="w-1.5 h-1.5 rounded-full animate-pulse"
          style={{ backgroundColor: currentConfig.color }}
        />
        <span>{currentConfig.label}</span>
      </div>
    </div>
  );
};
