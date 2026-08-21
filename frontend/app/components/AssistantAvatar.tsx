"use client";

import React from "react";
import { motion } from "framer-motion";
import { useAssistantState } from "../hooks/useAssistantState";
import { STATE_CONFIG } from "./types";
import { Mic, Sparkles, Volume2, Cpu, Bot } from "lucide-react";

/**
 * AssistantAvatar — Voice-first reactive glowing core circle & neural orb.
 * Dynamically reacts to state transitions and live audio amplitude.
 */
export const AssistantAvatar: React.FC = () => {
  const { state, audioAmplitude } = useAssistantState();
  const cfg = STATE_CONFIG[state];

  // Dynamic scale calculation reacting to real-time voice amplitude
  const dynamicAmpScale = 1 + audioAmplitude * 0.18;

  // Icon corresponding to the active assistant state
  const renderStateIcon = () => {
    switch (state) {
      case "listening":
        return <Mic className="w-12 h-12 text-emerald-300 drop-shadow-[0_0_15px_rgba(16,185,129,0.8)]" />;
      case "thinking":
        return <Sparkles className="w-12 h-12 text-amber-300 animate-spin-slow drop-shadow-[0_0_15px_rgba(245,158,11,0.8)]" />;
      case "speaking":
        return <Volume2 className="w-12 h-12 text-purple-300 drop-shadow-[0_0_20px_rgba(168,85,247,0.9)]" />;
      case "tool_use":
        return <Cpu className="w-12 h-12 text-cyan-300 animate-pulse drop-shadow-[0_0_15px_rgba(6,182,212,0.8)]" />;
      default:
        return <Bot className="w-12 h-12 text-cyan-300 drop-shadow-[0_0_15px_rgba(0,240,255,0.7)]" />;
    }
  };

  return (
    <div className="relative flex items-center justify-center">
      {/* Outer ambient glow field */}
      <motion.div
        className="absolute rounded-full pointer-events-none"
        style={{
          width: "clamp(260px, 32vw, 380px)",
          height: "clamp(260px, 32vw, 380px)",
          background: `radial-gradient(circle, rgba(${cfg.glowRgb}, 0.25) 0%, rgba(${cfg.glowRgb}, 0.08) 50%, transparent 75%)`,
        }}
        animate={{
          scale: [1, 1.08 * dynamicAmpScale, 1],
          opacity: [0.6, 0.9, 0.6],
        }}
        transition={{
          duration: state === "idle" ? 3.5 : 1.2,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* Rotating outer dashed ring */}
      <motion.div
        className="absolute rounded-full pointer-events-none border border-dashed"
        style={{
          width: "clamp(240px, 30vw, 350px)",
          height: "clamp(240px, 30vw, 350px)",
          borderColor: `rgba(${cfg.glowRgb}, 0.35)`,
        }}
        animate={{
          rotate: 360,
          scale: [1, 1.03, 1],
        }}
        transition={{
          rotate: {
            duration: state === "thinking" ? 10 : 25,
            repeat: Infinity,
            ease: "linear",
          },
          scale: {
            duration: 2.5,
            repeat: Infinity,
            ease: "easeInOut",
          },
        }}
      />

      {/* Counter-rotating inner ring */}
      <motion.div
        className="absolute rounded-full pointer-events-none border border-dotted"
        style={{
          width: "clamp(200px, 25vw, 290px)",
          height: "clamp(200px, 25vw, 290px)",
          borderColor: `rgba(${cfg.glowRgb}, 0.5)`,
        }}
        animate={{
          rotate: -360,
        }}
        transition={{
          duration: state === "listening" ? 8 : 18,
          repeat: Infinity,
          ease: "linear",
        }}
      />

      {/* Central Glassmorphic Glowing Core Orb */}
      <motion.div
        className="relative rounded-full flex flex-col items-center justify-center shadow-2xl backdrop-blur-2xl overflow-hidden border"
        style={{
          width: "clamp(180px, 22vw, 260px)",
          height: "clamp(180px, 22vw, 260px)",
          background: `radial-gradient(circle at 35% 35%, rgba(${cfg.glowRgb}, 0.28), rgba(10, 17, 34, 0.92) 70%)`,
          borderColor: `rgba(${cfg.glowRgb}, 0.6)`,
          boxShadow: `0 0 50px rgba(${cfg.glowRgb}, 0.35), inset 0 0 35px rgba(${cfg.glowRgb}, 0.2)`,
        }}
        animate={{
          scale: dynamicAmpScale,
          borderColor: `rgba(${cfg.glowRgb}, 0.8)`,
          boxShadow: `0 0 ${40 + audioAmplitude * 50}px rgba(${cfg.glowRgb}, ${0.35 + audioAmplitude * 0.4}), inset 0 0 30px rgba(${cfg.glowRgb}, 0.25)`,
        }}
        transition={{ type: "spring", stiffness: 200, damping: 18 }}
      >
        {/* Core pulsing orb layer */}
        <motion.div
          className="absolute inset-4 rounded-full pointer-events-none"
          style={{
            background: `radial-gradient(circle, rgba(${cfg.glowRgb}, 0.3) 0%, transparent 70%)`,
          }}
          animate={{
            scale: [0.9, 1.15, 0.9],
            opacity: [0.5, 0.9, 0.5],
          }}
          transition={{
            duration: state === "idle" ? 2.5 : 1,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        {/* Central State Icon */}
        <motion.div
          className="z-10 flex items-center justify-center"
          animate={{
            scale: [1, 1.08, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          {renderStateIcon()}
        </motion.div>

        {/* Status Pill Inside Circle */}
        <motion.div
          className="z-10 mt-3 px-3 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-widest uppercase border backdrop-blur-md"
          style={{
            backgroundColor: `rgba(${cfg.glowRgb}, 0.15)`,
            borderColor: `rgba(${cfg.glowRgb}, 0.5)`,
            color: cfg.color,
          }}
        >
          <span className="flex items-center gap-1.5">
            <motion.span
              className="w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: cfg.color }}
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.7, 1, 0.7],
              }}
              transition={{
                duration: state === "idle" ? 2 : 0.8,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
            {cfg.label}
          </span>
        </motion.div>
      </motion.div>
    </div>
  );
};
