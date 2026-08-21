"use client";
/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState } from "react";
import {
  Sparkles,
  Zap,
  ArrowRight,
  Layers,
} from "lucide-react";

import { InterviewerAvatar } from "./InterviewerAvatar";
import { DocumentUploadCard } from "./DocumentUploadCard";
import { PreInterviewAnalysis } from "./PreInterviewAnalysis";

const DOMAINS = [
  "Full Stack Development",
  "Frontend Development",
  "Backend Development",
  "Software Engineering",
  "Data Science",
  "Machine Learning",
  "AI / ML",
  "DevOps",
  "Cloud Engineering",
  "Cybersecurity",
  "Mobile Development",
  "Java Development",
  "Python Development",
  "C++ Development",
  "JavaScript Development",
  "Database / SQL",
  "System Design",
];

const EXPERIENCE_LEVELS = [
  "Fresher",
  "0–1 Years",
  "1–3 Years",
  "3–5 Years",
  "5+ Years",
];

const PROGRAMMING_LANGUAGES = [
  "C++",
  "Java",
  "Python",
  "JavaScript",
  "TypeScript",
  "Go",
  "Rust",
  "C#",
];

export const InterviewProtocol: React.FC = () => {
  const [resumeData, setResumeData] = useState<any | null>(null);
  const [jdData, setJdData] = useState<any | null>(null);
  const [selectedDomain, setSelectedDomain] = useState<string>("Full Stack Development");
  const [autoDetectDomain, setAutoDetectDomain] = useState<boolean>(true);
  const [experienceLevel, setExperienceLevel] = useState<string>("1–3 Years");
  const [programmingLanguage, setProgrammingLanguage] = useState<string>("Python");
  
  const [isInitializing, setIsInitializing] = useState<boolean>(false);
  const [isReady, setIsReady] = useState<boolean>(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const handleJdExtracted = (data: any) => {
    setJdData(data);
    if (data && autoDetectDomain && data.inferred_domain) {
      const match = DOMAINS.find(
        (d) => d.toLowerCase() === data.inferred_domain.toLowerCase()
      );
      if (match) {
        setSelectedDomain(match);
      }
    }
  };

  const handleStartAnalysis = async () => {
    if (!resumeData || !jdData) {
      setSessionError("Please upload both Candidate Resume and Job Description before proceeding.");
      return;
    }

    setSessionError(null);
    setIsInitializing(true);

    try {
      // Persist Phase 1 Intake Session
      const res = await fetch("http://127.0.0.1:8005/api/interview/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_data: resumeData,
          job_description_data: jdData,
          domain: selectedDomain,
          experience_level: experienceLevel,
          programming_language: programmingLanguage,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to initialize interview session.");
      }

      setIsReady(true);
    } catch (err: any) {
      setSessionError(err.message || "Failed to persist intake configuration.");
      setIsInitializing(false);
    }
  };

  const handleReset = () => {
    setResumeData(null);
    setJdData(null);
    setIsInitializing(false);
    setIsReady(false);
    setSessionError(null);
  };

  if (isReady) {
    return (
      <div className="relative z-10 w-full max-w-5xl mx-auto px-4 py-8">
        <PreInterviewAnalysis
          resumeData={resumeData}
          jdData={jdData}
          domain={selectedDomain}
          experienceLevel={experienceLevel}
          programmingLanguage={programmingLanguage}
          onReset={handleReset}
        />
      </div>
    );
  }

  const isFormComplete = !!resumeData && !!jdData;

  return (
    <div className="relative z-10 w-full max-w-5xl mx-auto px-4 py-8 flex flex-col gap-8 font-mono">
      {/* ─── Hero Setup Banner ─── */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-6 glass-panel p-6 sm:p-8 rounded-3xl border border-cyan-500/30 shadow-[0_0_40px_rgba(0,240,255,0.12)]">
        <div className="flex flex-col gap-2 text-center md:text-left">
          <div className="flex items-center justify-center md:justify-start gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 text-[10px] font-bold tracking-widest uppercase">
              AGENTIC PROTOCOL
            </span>
            <span className="text-[10px] text-gray-400">PHASE 1 INTAKE</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-black text-cyan-300 tracking-wider">
            VOCALIS AI — INTERVIEW PROTOCOL
          </h1>
          <p className="text-xs sm:text-sm text-gray-300 max-w-xl leading-relaxed">
            Adaptive AI-powered technical interview system. Upload candidate CV and target job specification to calibrate the autonomous evaluator.
          </p>
        </div>

        {/* Holographic Interviewer Avatar */}
        <div className="flex-shrink-0">
          <InterviewerAvatar />
        </div>
      </div>

      {/* ─── Intake Documents Section (Step 1 & Step 2) ─── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        {/* Step 1: Candidate CV */}
        <DocumentUploadCard
          title="Candidate Resume / CV"
          subtitle="Upload candidate portfolio (.pdf, .docx, .txt)"
          type="cv"
          endpoint="/api/interview/upload-resume"
          onExtracted={(data) => setResumeData(data)}
          extractedData={resumeData}
        />

        {/* Step 2: Job Description */}
        <DocumentUploadCard
          title="Target Job Description"
          subtitle="Upload role requirements & specifications"
          type="jd"
          endpoint="/api/interview/upload-jd"
          onExtracted={handleJdExtracted}
          extractedData={jdData}
        />
      </div>

      {/* ─── Configuration Matrix (Domain, Experience, Language) ─── */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col gap-6 border border-cyan-500/20">
        <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
              Technical Assessment Calibration
            </h3>
          </div>
          <span className="text-[10px] text-gray-500">Evaluation Matrix Config</span>
        </div>

        {/* Domain Selection */}
        <div className="flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <label className="text-xs text-gray-300 font-bold flex items-center gap-1.5">
              <span>Target Technical Track / Domain:</span>
            </label>

            {/* Auto Detect Toggle */}
            <button
              type="button"
              onClick={() => {
                const next = !autoDetectDomain;
                setAutoDetectDomain(next);
                if (next && jdData?.inferred_domain) {
                  const match = DOMAINS.find(
                    (d) => d.toLowerCase() === jdData.inferred_domain.toLowerCase()
                  );
                  if (match) setSelectedDomain(match);
                }
              }}
              className={`px-2.5 py-1 rounded-full text-[10px] transition border flex items-center gap-1.5 ${
                autoDetectDomain
                  ? "bg-cyan-950 border-cyan-500/50 text-cyan-300 font-bold shadow-[0_0_12px_rgba(0,240,255,0.3)]"
                  : "bg-slate-900 border-slate-700 text-gray-400"
              }`}
            >
              <Sparkles className="w-3 h-3 text-cyan-400" />
              <span>AUTO DETECT FROM JOB DESCRIPTION</span>
            </button>
          </div>

          {/* Domain Chips Grid */}
          <div className="flex flex-wrap gap-1.5">
            {DOMAINS.map((domain) => {
              const isSelected = selectedDomain === domain;
              return (
                <button
                  key={domain}
                  type="button"
                  onClick={() => {
                    setSelectedDomain(domain);
                    setAutoDetectDomain(false);
                  }}
                  className={`px-3 py-1.5 rounded-xl text-xs transition-all border ${
                    isSelected
                      ? "bg-cyan-500/20 border-cyan-400 text-cyan-200 font-bold shadow-[0_0_15px_rgba(0,240,255,0.25)]"
                      : "bg-slate-950/60 border-slate-800 text-gray-400 hover:text-gray-200 hover:border-slate-700"
                  }`}
                >
                  {domain}
                </button>
              );
            })}
          </div>
        </div>

        {/* Experience Level & Programming Language Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 border-t border-slate-800">
          {/* Experience Level */}
          <div className="flex flex-col gap-2">
            <label className="text-xs text-gray-300 font-bold">
              Target Seniority / Experience Level:
            </label>
            <div className="flex flex-wrap gap-1.5">
              {EXPERIENCE_LEVELS.map((exp) => (
                <button
                  key={exp}
                  type="button"
                  onClick={() => setExperienceLevel(exp)}
                  className={`px-3 py-1.5 rounded-xl text-xs transition-all border ${
                    experienceLevel === exp
                      ? "bg-emerald-500/20 border-emerald-400 text-emerald-300 font-bold shadow-[0_0_12px_rgba(16,185,129,0.25)]"
                      : "bg-slate-950/60 border-slate-800 text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {exp}
                </button>
              ))}
            </div>
          </div>

          {/* Programming Language */}
          <div className="flex flex-col gap-2">
            <label className="text-xs text-gray-300 font-bold">
              Primary Assessment Language:
            </label>
            <div className="flex flex-wrap gap-1.5">
              {PROGRAMMING_LANGUAGES.map((lang) => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => setProgrammingLanguage(lang)}
                  className={`px-3 py-1.5 rounded-xl text-xs transition-all border ${
                    programmingLanguage === lang
                      ? "bg-purple-500/20 border-purple-400 text-purple-300 font-bold shadow-[0_0_12px_rgba(168,85,247,0.25)]"
                      : "bg-slate-950/60 border-slate-800 text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {sessionError && (
        <div className="p-3 rounded-xl bg-red-950/80 border border-red-500/50 text-red-300 text-xs text-center">
          {sessionError}
        </div>
      )}

      {/* ─── Initialization CTA Button ─── */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 glass-panel p-4 rounded-2xl border border-cyan-500/25">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <div className={`w-2 h-2 rounded-full ${isFormComplete ? "bg-emerald-400" : "bg-amber-400"}`} />
          <span>
            {isFormComplete
              ? "All intake requirements satisfied. Ready to initialize protocol."
              : "Upload both Resume & Job Description to activate initialization."}
          </span>
        </div>

        <button
          type="button"
          disabled={!isFormComplete || isInitializing}
          onClick={handleStartAnalysis}
          className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-black font-bold text-xs font-mono tracking-wider uppercase hover:brightness-110 disabled:opacity-40 transition shadow-[0_0_25px_rgba(0,240,255,0.4)] flex items-center justify-center gap-2"
        >
          <Zap className="w-4 h-4" />
          <span>INITIALIZE INTERVIEW PROTOCOL</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
