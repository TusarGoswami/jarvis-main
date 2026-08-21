"use client";
/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  RotateCcw,
} from "lucide-react";

interface PreInterviewAnalysisProps {
  resumeData: any;
  jdData: any;
  domain: string;
  experienceLevel: string;
  programmingLanguage: string;
  onReset: () => void;
}

const INIT_STEPS = [
  { id: 1, label: "Parsing CV Document & Structure" },
  { id: 2, label: "Parsing Job Description Specifications" },
  { id: 3, label: "Detecting Candidate Core Technical Skills" },
  { id: 4, label: "Mapping Candidate Profile → Job Requirements" },
  { id: 5, label: "Preparing Adaptive Technical Question Bank" },
  { id: 6, label: "Initializing Neural AI Interviewer Persona" },
  { id: 7, label: "Initializing Real-Time Integrity & Visual Monitor" },
];

export const PreInterviewAnalysis: React.FC<PreInterviewAnalysisProps> = ({
  resumeData,
  jdData,
  domain,
  experienceLevel,
  programmingLanguage,
  onReset,
}) => {
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    let current = 0;
    const interval = setInterval(() => {
      current += 1;
      if (current <= INIT_STEPS.length) {
        setCompletedSteps((prev) => [...prev, current]);
      } else {
        setIsDone(true);
        clearInterval(interval);
      }
    }, 450);

    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-panel p-6 sm:p-8 rounded-3xl flex flex-col gap-6 max-w-3xl w-full mx-auto border border-cyan-500/40 shadow-[0_0_50px_rgba(0,240,255,0.2)] font-mono"
    >
      {/* Title */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 pb-4">
        <div>
          <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-widest flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            VOCALIS INTERVIEW ENGINE
          </span>
          <h2 className="text-xl font-black text-cyan-300 tracking-wide mt-0.5">
            SYSTEM INITIALIZATION PROTOCOL
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold border transition-all ${
              isDone
                ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.4)]"
                : "bg-cyan-950/80 border-cyan-500/40 text-cyan-300 animate-pulse"
            }`}
          >
            {isDone ? "INTERVIEW SYSTEM READY" : "DIAGNOSTICS IN PROGRESS"}
          </span>
        </div>
      </div>

      {/* Step-by-Step Animated Checklist */}
      <div className="bg-slate-950/80 p-4 sm:p-5 rounded-2xl border border-slate-800 flex flex-col gap-2.5">
        {INIT_STEPS.map((step) => {
          const isComplete = completedSteps.includes(step.id);
          const isCurrent = completedSteps.length === step.id - 1;

          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className={`flex items-center justify-between p-2.5 rounded-xl border text-xs transition-all ${
                isComplete
                  ? "bg-emerald-950/30 border-emerald-500/30 text-gray-200"
                  : isCurrent
                  ? "bg-cyan-950/40 border-cyan-500/40 text-cyan-200 shadow-[0_0_15px_rgba(0,240,255,0.15)]"
                  : "bg-black/30 border-slate-900 text-gray-500"
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-gray-500 text-[10px]">0{step.id}</span>
                <span>{step.label}</span>
              </div>
              <div>
                {isComplete ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isCurrent ? (
                  <RefreshCw className="w-4 h-4 text-cyan-400 animate-spin" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-slate-800" />
                )}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Profile & Target Mapping Summary */}
      {isDone && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-4"
        >
          {/* Summary Matrix Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-cyan-500/30 flex flex-col gap-1">
              <span className="text-[10px] text-gray-400 uppercase">Target Role &amp; Domain</span>
              <span className="text-cyan-300 font-bold text-sm truncate">{jdData?.title || domain}</span>
              <span className="text-[10px] text-gray-500">{domain} ({experienceLevel})</span>
            </div>

            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-emerald-500/30 flex flex-col gap-1">
              <span className="text-[10px] text-gray-400 uppercase">Candidate Name</span>
              <span className="text-emerald-300 font-bold text-sm truncate">
                {resumeData?.name || "Candidate"}
              </span>
              <span className="text-[10px] text-gray-500">
                {resumeData?.skills?.length || 0} Skills Detected
              </span>
            </div>

            <div className="bg-slate-950/80 p-3.5 rounded-xl border border-purple-500/30 flex flex-col gap-1">
              <span className="text-[10px] text-gray-400 uppercase">Coding Language</span>
              <span className="text-purple-300 font-bold text-sm">{programmingLanguage}</span>
              <span className="text-[10px] text-gray-500">Live Coding Sandbox Ready</span>
            </div>
          </div>

          {/* Phase 1 Completion Banner */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-cyan-950/80 via-slate-900 to-blue-950/80 border border-cyan-500/40 text-center flex flex-col items-center justify-center gap-2">
            <div className="flex items-center gap-2 text-cyan-300 font-bold text-sm">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              <span>Phase 1 Scaffolding &amp; Document Intake Complete</span>
            </div>
            <p className="text-xs text-gray-300 max-w-lg leading-relaxed">
              Candidate profile and job requirements successfully extracted, validated, and persisted. 
              The adaptive question generator, voice interviewer, live coding round, and scoring engine will initialize in Phase 2.
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={onReset}
              className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-gray-300 hover:text-white transition flex items-center gap-1.5 text-xs"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset &amp; Configure Another</span>
            </button>

            <button
              onClick={() => alert("Phase 1 Complete! Interactive question generation and live interview engine are ready for Phase 2 implementation.")}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-black font-bold text-xs hover:brightness-110 transition shadow-[0_0_20px_rgba(0,240,255,0.4)] flex items-center gap-2"
            >
              <span>Begin Assessment (Phase 2 Ready)</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};
