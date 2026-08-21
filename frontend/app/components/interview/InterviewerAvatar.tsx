"use client";

import React from "react";
import { motion } from "framer-motion";
import { UserCheck, Sparkles } from "lucide-react";

/**
 * InterviewerAvatar — Futuristic illustrative AI Interviewer holographic avatar.
 * Adheres strictly to requirements: professional generative illustrative persona,
 * non-celebrity, matching Vocalis cyber HUD visual language.
 */
export const InterviewerAvatar: React.FC = () => {
  return (
    <div className="relative flex flex-col items-center justify-center">
      {/* Outer ambient biometric scanner ring */}
      <motion.div
        className="absolute rounded-full pointer-events-none border border-cyan-500/30"
        style={{
          width: "180px",
          height: "180px",
        }}
        animate={{
          scale: [1, 1.08, 1],
          opacity: [0.3, 0.7, 0.3],
          rotate: 360,
        }}
        transition={{
          scale: { duration: 3, repeat: Infinity, ease: "easeInOut" },
          opacity: { duration: 3, repeat: Infinity, ease: "easeInOut" },
          rotate: { duration: 30, repeat: Infinity, ease: "linear" },
        }}
      />

      {/* Counter-rotating dashed aura */}
      <motion.div
        className="absolute rounded-full pointer-events-none border border-dashed border-cyan-400/40"
        style={{
          width: "160px",
          height: "160px",
        }}
        animate={{
          rotate: -360,
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "linear",
        }}
      />

      {/* Main Avatar Centerpiece */}
      <motion.div
        className="relative w-32 h-32 rounded-2xl bg-gradient-to-b from-slate-900 via-slate-950 to-cyan-950/80 border border-cyan-500/50 shadow-[0_0_35px_rgba(0,240,255,0.25)] flex flex-col items-center justify-center overflow-hidden backdrop-blur-xl"
        whileHover={{ scale: 1.03 }}
        transition={{ type: "spring", stiffness: 200, damping: 20 }}
      >
        {/* Holographic grid overlay */}
        <div className="absolute inset-0 bg-[radial-gradient(#00f0ff_1px,transparent_1px)] [background-size:12px_12px] opacity-25 pointer-events-none" />

        {/* Generative Persona Silhouette / Hologram */}
        <div className="relative z-10 flex flex-col items-center justify-center">
          <div className="w-14 h-14 rounded-full bg-cyan-500/15 border border-cyan-400/60 flex items-center justify-center shadow-[0_0_20px_rgba(0,240,255,0.4)]">
            <UserCheck className="w-7 h-7 text-cyan-300" />
          </div>
          <div className="mt-2 flex items-center gap-1 text-[10px] font-mono font-bold tracking-widest text-cyan-400 uppercase">
            <Sparkles className="w-2.5 h-2.5 text-cyan-400 animate-pulse" />
            <span>VOCALIS EVALUATOR</span>
          </div>
        </div>

        {/* Scanning telemetry sweep line */}
        <motion.div
          className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_10px_#00f0ff]"
          animate={{
            top: ["0%", "100%", "0%"],
          }}
          transition={{
            duration: 3.5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </motion.div>

      {/* Sub-badge: Autonomous Evaluator Active */}
      <div className="mt-3 flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-950/80 border border-cyan-500/30 text-[10px] font-mono text-gray-300">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        <span>NEURAL INTERVIEW AGENT v2.0</span>
      </div>
    </div>
  );
};
