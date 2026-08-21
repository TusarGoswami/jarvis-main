"use client";
/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Download,
  BookOpen,
  Zap,
  Layers,
  Eye,
} from "lucide-react";

interface InterviewResultsDashboardProps {
  report: any;
  session: any;
  onExit: () => void;
}

export const InterviewResultsDashboard: React.FC<InterviewResultsDashboardProps> = ({
  report,
  session,
  onExit,
}) => {
  const [expandedQuestion, setExpandedQuestion] = useState<number | null>(null);

  const overallScore = report?.overall_score ?? 7.0;
  const recommendation = report?.final_recommendation ?? "Borderline";
  const history = session?.questions_history || [];
  const integrityEvents = report?.integrity_events || session?.integrity_events || [];
  const integrityScore = report?.interview_integrity ?? 10.0;

  // Recommendation Badge Colors
  const getRecommendationBadge = () => {
    switch (recommendation.toLowerCase()) {
      case "strong hire":
        return {
          bg: "bg-emerald-950/90 border-emerald-400 text-emerald-300",
          shadow: "shadow-[0_0_30px_rgba(16,185,129,0.45)]",
          icon: Award,
        };
      case "hire":
        return {
          bg: "bg-cyan-950/90 border-cyan-400 text-cyan-300",
          shadow: "shadow-[0_0_30px_rgba(0,240,255,0.45)]",
          icon: CheckCircle2,
        };
      case "borderline":
        return {
          bg: "bg-amber-950/90 border-amber-400 text-amber-300",
          shadow: "shadow-[0_0_30px_rgba(245,158,11,0.45)]",
          icon: AlertTriangle,
        };
      default:
        return {
          bg: "bg-red-950/90 border-red-400 text-red-300",
          shadow: "shadow-[0_0_30px_rgba(239,68,68,0.45)]",
          icon: XCircle,
        };
    }
  };

  const recConfig = getRecommendationBadge();
  const RecIcon = recConfig.icon;

  return (
    <div className="relative z-10 w-full max-w-6xl mx-auto px-4 py-8 flex flex-col gap-8 font-mono">
      {/* ─── Hero Overall Scorecard Banner ─── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-panel p-6 sm:p-8 rounded-3xl border border-cyan-500/40 shadow-[0_0_50px_rgba(0,240,255,0.18)] flex flex-col md:flex-row items-center justify-between gap-6"
      >
        <div className="flex flex-col gap-2 text-center md:text-left">
          <div className="flex items-center justify-center md:justify-start gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-[10px] font-bold uppercase tracking-widest">
              OFFICIAL EVALUATION DOSSIER
            </span>
            <span className="text-[10px] text-gray-400">STRICT EVIDENCE-BASED AUDIT</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-black text-cyan-200">
            {session?.resume_data?.name || "Candidate"} — Assessment Results
          </h1>
          <p className="text-xs sm:text-sm text-gray-300 max-w-xl font-sans leading-relaxed">
            Track: <strong className="text-cyan-300">{session?.domain}</strong> ({session?.experience_level}, {session?.programming_language})
          </p>
        </div>

        {/* Big Overall Score & Recommendation Pill */}
        <div className="flex flex-col items-center gap-3">
          <div className="flex items-center gap-4 bg-black/60 p-4 rounded-2xl border border-cyan-500/30">
            <div className="flex flex-col items-center">
              <span className="text-[10px] text-gray-400 font-bold uppercase">OVERALL SCORE</span>
              <span className="text-3xl sm:text-4xl font-black text-cyan-300">
                {overallScore}<span className="text-sm text-gray-500 font-normal">/10</span>
              </span>
            </div>

            <div className="w-px h-12 bg-slate-800" />

            <div className={`px-4 py-2 rounded-xl border flex items-center gap-2 ${recConfig.bg} ${recConfig.shadow}`}>
              <RecIcon className="w-5 h-5" />
              <div className="flex flex-col">
                <span className="text-[9px] uppercase tracking-wider text-gray-400">VERDICT</span>
                <span className="text-sm font-black uppercase tracking-wider">{recommendation}</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* ─── 5 Core Competency Metric Grid ─── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {/* Technical Knowledge */}
        <div className="glass-panel p-4 rounded-2xl border border-cyan-500/25 flex flex-col gap-1.5 shadow-md">
          <span className="text-[10px] text-gray-400 uppercase font-bold">Technical Depth</span>
          <span className="text-2xl font-black text-cyan-300">
            {report?.technical_knowledge ?? 7.0}<span className="text-xs text-gray-500 font-normal">/10</span>
          </span>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-cyan-400 h-full rounded-full"
              style={{ width: `${(report?.technical_knowledge ?? 7.0) * 10}%` }}
            />
          </div>
        </div>

        {/* Problem Solving */}
        <div className="glass-panel p-4 rounded-2xl border border-blue-500/25 flex flex-col gap-1.5 shadow-md">
          <span className="text-[10px] text-gray-400 uppercase font-bold">Problem Solving</span>
          <span className="text-2xl font-black text-blue-300">
            {report?.problem_solving ?? 6.5}<span className="text-xs text-gray-500 font-normal">/10</span>
          </span>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-blue-400 h-full rounded-full"
              style={{ width: `${(report?.problem_solving ?? 6.5) * 10}%` }}
            />
          </div>
        </div>

        {/* Communication */}
        <div className="glass-panel p-4 rounded-2xl border border-purple-500/25 flex flex-col gap-1.5 shadow-md">
          <span className="text-[10px] text-gray-400 uppercase font-bold">Communication</span>
          <span className="text-2xl font-black text-purple-300">
            {report?.communication ?? 7.5}<span className="text-xs text-gray-500 font-normal">/10</span>
          </span>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-purple-400 h-full rounded-full"
              style={{ width: `${(report?.communication ?? 7.5) * 10}%` }}
            />
          </div>
        </div>

        {/* Answer Accuracy */}
        <div className="glass-panel p-4 rounded-2xl border border-emerald-500/25 flex flex-col gap-1.5 shadow-md">
          <span className="text-[10px] text-gray-400 uppercase font-bold">Answer Accuracy</span>
          <span className="text-2xl font-black text-emerald-300">
            {report?.answer_accuracy ?? 7.0}<span className="text-xs text-gray-500 font-normal">/10</span>
          </span>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-emerald-400 h-full rounded-full"
              style={{ width: `${(report?.answer_accuracy ?? 7.0) * 10}%` }}
            />
          </div>
        </div>

        {/* Interview Integrity */}
        <div
          className={`glass-panel p-4 rounded-2xl border flex flex-col gap-1.5 shadow-md ${
            integrityScore >= 8
              ? "border-emerald-500/40"
              : integrityScore >= 5
              ? "border-amber-500/40"
              : "border-red-500/40"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-gray-400 uppercase font-bold">Session Integrity</span>
            {integrityScore >= 8 ? (
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            )}
          </div>
          <span
            className={`text-2xl font-black ${
              integrityScore >= 8
                ? "text-emerald-300"
                : integrityScore >= 5
                ? "text-amber-300"
                : "text-red-300"
            }`}
          >
            {integrityScore}<span className="text-xs text-gray-500 font-normal">/10</span>
          </span>
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                integrityScore >= 8 ? "bg-emerald-400" : integrityScore >= 5 ? "bg-amber-400" : "bg-red-400"
              }`}
              style={{ width: `${integrityScore * 10}%` }}
            />
          </div>
        </div>
      </div>

      {/* ─── Executive Summary Quote ─── */}
      {report?.evaluator_summary && (
        <div className="glass-panel p-5 rounded-2xl border border-cyan-500/25 bg-slate-950/80 flex flex-col gap-1.5">
          <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-cyan-400" /> Evaluator Verdict Summary
          </span>
          <p className="text-xs sm:text-sm text-gray-200 font-sans leading-relaxed italic">
            &ldquo;{report.evaluator_summary}&rdquo;
          </p>
        </div>
      )}

      {/* ─── Strengths, Weaknesses & Critical Knowledge Gaps (3 Columns) ─── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        {/* Strengths */}
        <div className="glass-panel p-5 rounded-2xl border border-emerald-500/30 flex flex-col gap-3">
          <div className="flex items-center gap-2 border-b border-emerald-500/20 pb-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-300">
              Demonstrated Strengths
            </h3>
          </div>
          <ul className="space-y-2 text-xs font-sans text-gray-300 leading-relaxed list-disc list-inside">
            {report?.strengths?.map((s: string, i: number) => (
              <li key={i} className="marker:text-emerald-400">
                <span>{s}</span>
              </li>
            )) || <li>Solid grasp of core language features.</li>}
          </ul>
        </div>

        {/* Weaknesses */}
        <div className="glass-panel p-5 rounded-2xl border border-amber-500/30 flex flex-col gap-3">
          <div className="flex items-center gap-2 border-b border-amber-500/20 pb-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-amber-300">
              Identified Weaknesses
            </h3>
          </div>
          <ul className="space-y-2 text-xs font-sans text-gray-300 leading-relaxed list-disc list-inside">
            {report?.weaknesses?.map((w: string, i: number) => (
              <li key={i} className="marker:text-amber-400">
                <span>{w}</span>
              </li>
            )) || <li>Limited tradeoff depth on edge-case scenarios.</li>}
          </ul>
        </div>

        {/* Critical Knowledge Gaps */}
        <div className="glass-panel p-5 rounded-2xl border border-red-500/30 flex flex-col gap-3">
          <div className="flex items-center gap-2 border-b border-red-500/20 pb-2.5">
            <BookOpen className="w-4 h-4 text-red-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-red-300">
              Critical Knowledge Gaps
            </h3>
          </div>
          <ul className="space-y-2 text-xs font-sans text-gray-300 leading-relaxed list-disc list-inside">
            {report?.critical_knowledge_gaps?.map((g: string, i: number) => (
              <li key={i} className="marker:text-red-400">
                <span>{g}</span>
              </li>
            )) || <li>Distributed concurrency isolation boundaries.</li>}
          </ul>
        </div>
      </div>

      {/* ─── Question-by-Question Deep Dive Scorecard (Strict 0–10) ─── */}
      <div className="glass-panel rounded-2xl border border-cyan-500/25 overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
              Turn-by-Turn Scorecard &amp; Rubric Audit ({history.length} Questions)
            </h3>
          </div>
          <span className="text-[10px] text-gray-500">Strict 0–10 Scale</span>
        </div>

        <div className="divide-y divide-slate-800/80">
          {history.map((h: any, idx: number) => {
            const isExpanded = expandedQuestion === idx;
            const score = h.score ?? 5;
            return (
              <div key={idx} className="p-4 hover:bg-slate-950/50 transition flex flex-col gap-2">
                <div
                  onClick={() => setExpandedQuestion(isExpanded ? null : idx)}
                  className="cursor-pointer flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2.5 py-1 rounded-lg text-xs font-black uppercase font-mono border ${
                        score >= 8
                          ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-300"
                          : score >= 5
                          ? "bg-amber-950/80 border-amber-500/50 text-amber-300"
                          : "bg-red-950/80 border-red-500/50 text-red-300"
                      }`}
                    >
                      {score}/10
                    </span>

                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-gray-200 font-sans">
                        Q{idx + 1}: {h.question_text}
                      </span>
                      <span className="text-[10px] text-gray-500 font-mono">
                        Category: {h.category || "TECHNICAL"} • Level: {h.difficulty || "MEDIUM"}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                  </div>
                </div>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="mt-2 pt-3 border-t border-slate-800/60 flex flex-col gap-2.5 text-xs font-sans"
                    >
                      {/* Expected Concept */}
                      {h.expected_concept && (
                        <div className="bg-slate-950/90 p-3 rounded-xl border border-cyan-500/20 flex flex-col gap-1">
                          <span className="text-[10px] text-cyan-400 font-mono uppercase font-bold">
                            Expected Technical Concept:
                          </span>
                          <p className="text-gray-300">{h.expected_concept}</p>
                        </div>
                      )}

                      {/* Candidate Answer */}
                      <div className="bg-black/50 p-3 rounded-xl border border-slate-800 flex flex-col gap-1">
                        <span className="text-[10px] text-gray-400 font-mono uppercase font-bold">
                          Candidate&apos;s Submitted Response:
                        </span>
                        <p className="text-gray-200 font-mono whitespace-pre-wrap">{h.answer_text}</p>
                      </div>

                      {/* Detailed Evaluator Justification */}
                      <div className="bg-slate-950/90 p-3 rounded-xl border border-emerald-500/20 flex flex-col gap-1">
                        <span className="text-[10px] text-emerald-400 font-mono uppercase font-bold">
                          Evaluator Score Justification:
                        </span>
                        <p className="text-gray-300 font-mono leading-relaxed">{h.evaluation}</p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── Integrity Audit Log ─── */}
      <div className="glass-panel p-5 rounded-2xl border border-cyan-500/25 flex flex-col gap-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
              Integrity Event Timeline ({integrityEvents.length} Signals)
            </h3>
          </div>
          <span className="text-[10px] text-gray-500">Continuous Browser Telemetry</span>
        </div>

        {integrityEvents.length === 0 ? (
          <div className="text-xs font-mono text-emerald-400 p-3 bg-emerald-950/40 rounded-xl border border-emerald-500/30 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Zero suspicious events recorded. Session maintained full focus.</span>
          </div>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {integrityEvents.map((ev: any, idx: number) => (
              <div
                key={idx}
                className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  <span className="text-gray-200 font-bold">{ev.event_type}</span>
                  <span className="text-gray-500 text-[10px]">({ev.duration_seconds}s away)</span>
                </div>
                <span className="text-gray-500 text-[10px] font-mono">{ev.timestamp}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ─── Footer Action Bar ─── */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 glass-panel p-4 rounded-2xl border border-cyan-500/30">
        <button
          onClick={() => window.print()}
          className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-gray-300 hover:text-white transition flex items-center justify-center gap-2 text-xs font-bold"
        >
          <Download className="w-4 h-4" />
          <span>Save / Print PDF Scorecard</span>
        </button>

        <button
          onClick={onExit}
          className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-black font-bold text-xs uppercase tracking-wider hover:brightness-110 transition shadow-[0_0_20px_rgba(0,240,255,0.4)] flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Complete &amp; Return to Protocol</span>
        </button>
      </div>
    </div>
  );
};
