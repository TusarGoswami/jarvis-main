"use client";

import React from "react";
import { motion } from "framer-motion";
import { useAssistantState } from "../hooks/useAssistantState";
import { STATE_CONFIG, type AssistantState } from "./types";

const STATES: AssistantState[] = ["idle", "listening", "thinking", "speaking", "tool_use"];

/**
 * DevStateToggle — Development tool to cycle through assistant states
 * and control mock audio amplitude. Bottom-left corner, dev-only.
 */
export const DevStateToggle: React.FC = () => {
  const { state, audioAmplitude, devOverride, setDevOverride, setDevAmplitude } =
    useAssistantState();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="fixed bottom-20 left-4 z-30 glass-panel rounded-xl p-3 flex flex-col gap-2 text-xs font-mono"
      style={{ width: "180px" }}
    >
      <span className="text-gray-400 text-[10px] uppercase tracking-wider">
        Dev State Control
      </span>

      {/* State buttons */}
      <div className="flex flex-wrap gap-1">
        {STATES.map((s) => {
          const cfg = STATE_CONFIG[s];
          const isActive = (devOverride ?? state) === s;
          return (
            <button
              key={s}
              onClick={() => setDevOverride(devOverride === s ? null : s)}
              className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all border ${
                isActive
                  ? "border-current"
                  : "border-slate-700 text-gray-500 hover:text-gray-300"
              }`}
              style={isActive ? { color: cfg.color, borderColor: cfg.color } : {}}
            >
              {cfg.label}
            </button>
          );
        })}
      </div>

      {/* Amplitude slider */}
      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-[10px] text-gray-400">
          <span>Amplitude</span>
          <span className="text-cyan-300">{audioAmplitude.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={audioAmplitude}
          onChange={(e) => setDevAmplitude(parseFloat(e.target.value))}
          className="w-full accent-cyan-500 h-1"
        />
      </div>

      {/* Current state indicator */}
      <div className="text-[10px] text-gray-500 border-t border-slate-800 pt-1">
        Active: <span style={{ color: STATE_CONFIG[devOverride ?? state].color }}>
          {devOverride ?? state}
        </span>
        {devOverride && <span className="text-amber-400 ml-1">(override)</span>}
      </div>
    </motion.div>
  );
};
