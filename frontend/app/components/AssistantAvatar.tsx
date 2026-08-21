"use client";

import React from "react";
import { motion } from "framer-motion";
import { useAssistantState } from "../hooks/useAssistantState";
import { STATE_CONFIG } from "./types";

/**
 * AssistantAvatar — Sketchfab robot iframe with CSS-driven state reactions.
 *
 * All current animations are WRAPPER-LEVEL CSS only:
 *  - scale transforms on the container
 *  - box-shadow / drop-shadow glow changes
 *  - CSS filter (hue-rotate, brightness, saturate) on the iframe wrapper
 *  - border color transitions
 *
 * The Sketchfab iframe itself has no programmatic API control.
 * For actual model-level animation (idle breathing, head-turn, emissive pulse),
 * a future GLTF migration with react-three-fiber is required.
 */
export const AssistantAvatar: React.FC = () => {
  const { state } = useAssistantState();
  const cfg = STATE_CONFIG[state];

  // State-driven CSS wrapper variants
  const containerVariants = {
    idle: {
      scale: 1,
      filter: "brightness(1) saturate(1)",
      boxShadow: `0 0 40px rgba(${cfg.glowRgb}, 0.2), 0 0 80px rgba(${cfg.glowRgb}, 0.1)`,
    },
    listening: {
      scale: 1.03,
      filter: "brightness(1.1) saturate(1.2)",
      boxShadow: `0 0 60px rgba(${STATE_CONFIG.listening.glowRgb}, 0.4), 0 0 120px rgba(${STATE_CONFIG.listening.glowRgb}, 0.2)`,
    },
    thinking: {
      scale: 0.98,
      filter: "brightness(0.95) saturate(0.9) hue-rotate(15deg)",
      boxShadow: `0 0 50px rgba(${STATE_CONFIG.thinking.glowRgb}, 0.35), 0 0 100px rgba(${STATE_CONFIG.thinking.glowRgb}, 0.15)`,
    },
    speaking: {
      scale: 1.04,
      filter: "brightness(1.15) saturate(1.3)",
      boxShadow: `0 0 70px rgba(${STATE_CONFIG.speaking.glowRgb}, 0.5), 0 0 140px rgba(${STATE_CONFIG.speaking.glowRgb}, 0.25)`,
    },
    tool_use: {
      scale: 1.01,
      filter: "brightness(1.2) saturate(1.1) hue-rotate(-10deg)",
      boxShadow: `0 0 55px rgba(${STATE_CONFIG.tool_use.glowRgb}, 0.45), 0 0 110px rgba(${STATE_CONFIG.tool_use.glowRgb}, 0.2)`,
    },
  };

  return (
    <motion.div
      className="relative rounded-full overflow-hidden"
      style={{
        width: "clamp(280px, 35vw, 420px)",
        height: "clamp(280px, 35vw, 420px)",
      }}
      variants={containerVariants}
      animate={state}
      transition={{ type: "spring", stiffness: 120, damping: 20 }}
    >
      {/* Glow border ring */}
      <motion.div
        className="absolute inset-0 rounded-full pointer-events-none"
        style={{
          border: `2px solid ${cfg.color}`,
        }}
        animate={{
          borderColor: cfg.color,
          opacity: [0.6, 1, 0.6],
        }}
        transition={{
          borderColor: { type: "spring", stiffness: 100, damping: 15 },
          opacity: {
            duration: state === "idle" ? 3 : 1.5,
            repeat: Infinity,
            ease: "easeInOut",
          },
        }}
      />

      {/* Sketchfab iframe — pointer-events-none for display only */}
      <div
        className="w-full h-full rounded-full overflow-hidden"
        style={{ pointerEvents: "none" }}
      >
        <iframe
          title="Vocalis AI Assistant Avatar"
          src="https://sketchfab.com/models/9b0a8951830b4112aa8096a7fc09c9ff/embed?autostart=1&ui_infos=0&ui_controls=0&ui_stop=0&ui_inspector=0&ui_watermark=0&ui_watermark_link=0&ui_ar=0&ui_help=0&ui_settings=0&ui_vr=0&ui_fullscreen=0&ui_annotations=0&camera=0&transparent=1&preload=1"
          className="w-full h-full border-0"
          style={{
            transform: "scale(1.6)",
            transformOrigin: "center center",
          }}
          allow="autoplay; fullscreen; xr-spatial-tracking"
        />
      </div>

      {/* State label */}
      <motion.div
        className="absolute bottom-4 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-mono font-semibold tracking-widest uppercase backdrop-blur-sm"
        style={{
          backgroundColor: `rgba(${cfg.glowRgb}, 0.15)`,
          border: `1px solid rgba(${cfg.glowRgb}, 0.4)`,
          color: cfg.color,
        }}
        animate={{ color: cfg.color }}
        transition={{ type: "spring", stiffness: 100, damping: 15 }}
      >
        <span className="flex items-center gap-1.5">
          <motion.span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: cfg.color }}
            animate={{
              scale: [1, 1.4, 1],
              opacity: [0.7, 1, 0.7],
            }}
            transition={{
              duration: state === "idle" ? 2.5 : 1,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          {cfg.label}
        </span>
      </motion.div>
    </motion.div>
  );
};
