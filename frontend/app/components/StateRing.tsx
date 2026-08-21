"use client";

import React, { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useAssistantState } from "../hooks/useAssistantState";
import { STATE_CONFIG } from "./types";

const BAR_COUNT = 64;

/**
 * StateRing — Animated circular waveform ring surrounding the AssistantAvatar.
 *
 * Draws radially arranged bars that respond to audioAmplitude.
 * Color and behavior shift per assistant state (carried forward from ArcReactor's
 * color/speed scheme). Uses canvas for performance with framer-motion for
 * container-level spring transitions.
 */
export const StateRing: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const { state, audioAmplitude } = useAssistantState();
  const stateRef = useRef(state);
  const ampRef = useRef(audioAmplitude);
  const timeRef = useRef(0);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    ampRef.current = audioAmplitude;
  }, [audioAmplitude]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const render = () => {
      const size = canvas.width;
      const center = size / 2;
      const outerRadius = center - 10;
      const innerRadius = outerRadius - 35;

      ctx.clearRect(0, 0, size, size);

      const cfg = STATE_CONFIG[stateRef.current];
      const amp = ampRef.current;
      const speed = cfg.speed;

      timeRef.current += 0.016 * speed;
      const t = timeRef.current;

      for (let i = 0; i < BAR_COUNT; i++) {
        const angle = (i / BAR_COUNT) * Math.PI * 2 - Math.PI / 2;

        // Generate bar height from sine waves + audio amplitude
        const sineBase = Math.sin(t * 2 + i * 0.3) * 0.3 + 0.3;
        const sineSecondary = Math.sin(t * 3.7 + i * 0.7) * 0.15;
        const audioContrib = amp * (0.5 + Math.sin(t * 5 + i * 0.5) * 0.5);
        const barHeight = Math.max(
          0.1,
          Math.min(1, sineBase + sineSecondary + audioContrib)
        );

        const length = barHeight * (outerRadius - innerRadius);
        const startR = innerRadius;
        const endR = innerRadius + length;

        const x1 = center + Math.cos(angle) * startR;
        const y1 = center + Math.sin(angle) * startR;
        const x2 = center + Math.cos(angle) * endR;
        const y2 = center + Math.sin(angle) * endR;

        const alpha = 0.3 + barHeight * 0.7;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = `rgba(${cfg.glowRgb}, ${alpha})`;
        ctx.lineWidth = 2.5;
        ctx.lineCap = "round";
        ctx.stroke();
      }

      // Outer subtle circle
      ctx.beginPath();
      ctx.arc(center, center, outerRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${cfg.glowRgb}, 0.1)`;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Inner subtle circle
      ctx.beginPath();
      ctx.arc(center, center, innerRadius - 2, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${cfg.glowRgb}, 0.08)`;
      ctx.lineWidth = 1;
      ctx.stroke();

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, []);

  const cfg = STATE_CONFIG[state];

  return (
    <motion.div
      className="absolute inset-0 flex items-center justify-center pointer-events-none"
      animate={{
        filter: `drop-shadow(0 0 15px rgba(${cfg.glowRgb}, 0.3))`,
      }}
      transition={{ type: "spring", stiffness: 80, damping: 20 }}
    >
      <canvas
        ref={canvasRef}
        width={520}
        height={520}
        className="w-full h-full"
        style={{ maxWidth: "520px", maxHeight: "520px" }}
      />
    </motion.div>
  );
};
