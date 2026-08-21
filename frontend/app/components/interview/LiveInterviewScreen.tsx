"use client";
/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Clock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Activity,
  Layers,
  SkipForward,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
} from "lucide-react";

import { InterviewerAvatar } from "./InterviewerAvatar";
import type { AssistantState } from "../types";

interface LiveInterviewScreenProps {
  interviewId: string;
  onExit: () => void;
}

export const LiveInterviewScreen: React.FC<LiveInterviewScreenProps> = ({
  interviewId,
  onExit,
}) => {
  const [session, setSession] = useState<any | null>(null);
  const [answerText, setAnswerText] = useState<string>("");
  const [interimTranscript, setInterimTranscript] = useState<string>("");
  const [isListening, setIsListening] = useState<boolean>(false);
  const [interviewerState, setInterviewerState] = useState<AssistantState>("thinking");
  const [timeRemaining, setTimeRemaining] = useState<number>(3600);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const activityScrollRef = useRef<HTMLDivElement>(null);
  const waveCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const lastSpokenQIdRef = useRef<string | null>(null);

  // Format MM:SS
  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // 1. Synthesize & Speak Question via TTS
  const speakQuestionAudio = useCallback(async (text: string, qId?: string) => {
    if (!text) return;
    
    // Stop any existing playing audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }

    try {
      setInterviewerState("speaking");
      const res = await fetch("http://127.0.0.1:8005/api/agent/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, language: "en" }),
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        currentAudioRef.current = audio;

        audio.onended = () => {
          setInterviewerState("idle");
          if (qId) lastSpokenQIdRef.current = qId;
        };

        audio.onerror = () => {
          setInterviewerState("idle");
        };

        await audio.play();
      } else {
        setInterviewerState("idle");
      }
    } catch {
      setInterviewerState("idle");
    }
  }, []);

  const stopQuestionAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    setInterviewerState("idle");
  }, []);

  // 2. Fetch Session State
  const fetchSessionState = useCallback(async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8005/api/interview/${interviewId}/state`);
      if (res.ok) {
        const json = await res.json();
        setSession(json.data);
        if (json.data.time_remaining !== undefined) {
          setTimeRemaining(json.data.time_remaining);
        }
      }
    } catch {
      // Network retry
    } finally {
      setLoading(false);
    }
  }, [interviewId]);

  // Initial Session Start & Auto-Speak Question
  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      setLoading(true);
      try {
        const res = await fetch("http://127.0.0.1:8005/api/interview/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ interview_id: interviewId }),
        });
        if (res.ok && isMounted) {
          const json = await res.json();
          setSession(json.data);
          if (json.data.time_remaining !== undefined) {
            setTimeRemaining(json.data.time_remaining);
          }
          
          // Auto-speak opening question
          const q = json.data.current_question;
          if (q && q.text && lastSpokenQIdRef.current !== q.id) {
            lastSpokenQIdRef.current = q.id;
            speakQuestionAudio(q.text, q.id);
          } else {
            setInterviewerState("idle");
          }
        }
      } catch {
        if (isMounted) {
          setErrorMsg("Failed to connect to interview session. Retrying...");
          setInterviewerState("idle");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    init();
    return () => {
      isMounted = false;
    };
  }, [interviewId, speakQuestionAudio]);

  // 3. Server-Synced Countdown Timer
  useEffect(() => {
    const timerInterval = setInterval(() => {
      setTimeRemaining((prev) => Math.max(0, prev - 1));
    }, 1000);

    const syncInterval = setInterval(() => {
      fetchSessionState();
    }, 10000);

    return () => {
      clearInterval(timerInterval);
      clearInterval(syncInterval);
    };
  }, [interviewId, fetchSessionState]);

  // Auto-scroll activity log
  useEffect(() => {
    if (activityScrollRef.current) {
      activityScrollRef.current.scrollTop = activityScrollRef.current.scrollHeight;
    }
  }, [session?.activity_log?.length]);

  // 4. Real-Time Speech Recognition (STT) Setup
  const toggleListening = () => {
    // If AI is currently speaking, stop TTS first
    if (interviewerState === "speaking") {
      stopQuestionAudio();
    }

    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      setInterviewerState("idle");
      setInterimTranscript("");
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. You can type your response directly.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
        setInterviewerState("listening");
        setErrorMsg(null);
      };

      recognition.onresult = (event: any) => {
        let finalTrans = "";
        let currentInterim = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcriptChunk = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTrans += transcriptChunk + " ";
          } else {
            currentInterim += transcriptChunk;
          }
        }

        if (finalTrans) {
          setAnswerText((prev) => {
            const separator = prev.length > 0 && !prev.endsWith(" ") ? " " : "";
            return prev + separator + finalTrans;
          });
        }
        setInterimTranscript(currentInterim);
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition notice:", event.error);
        if (event.error === "not-allowed") {
          setIsListening(false);
          setInterviewerState("idle");
          setErrorMsg("Microphone permission denied. Switched to keyboard input.");
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        setInterimTranscript("");
        setInterviewerState((prev) => (prev === "listening" ? "idle" : prev));
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (e: any) {
      console.error("Speech Recognition Error:", e);
      setIsListening(false);
      setInterviewerState("idle");
    }
  };

  // Stop audio and recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
      }
    };
  }, []);

  // 5. Live Audio Waveform Canvas Animation
  useEffect(() => {
    if (!isListening && interviewerState !== "speaking") return;
    const canvas = waveCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let t = 0;

    const isSpeaking = interviewerState === "speaking";

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bars = 24;
      const barWidth = canvas.width / bars;

      for (let i = 0; i < bars; i++) {
        const h = (Math.sin(t * (isSpeaking ? 7 : 5) + i * 0.4) * 0.35 + 0.5) * canvas.height * 0.85;
        const x = i * barWidth + barWidth * 0.15;
        const y = (canvas.height - h) / 2;
        ctx.fillStyle = isSpeaking ? "rgba(168, 85, 247, 0.9)" : "rgba(16, 185, 129, 0.9)";
        ctx.fillRect(x, y, barWidth * 0.7, h);
      }
      t += 0.02;
      animId = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animId);
  }, [isListening, interviewerState]);

  // 6. Submit Candidate Answer
  const handleSubmitAnswer = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const finalAnswer = (answerText + (interimTranscript ? (answerText.length > 0 && !answerText.endsWith(" ") ? " " : "") + interimTranscript : "")).trim();
    if (!finalAnswer || submitting) return;

    if (isListening && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      setIsListening(false);
    }
    stopQuestionAudio();

    setAnswerText("");
    setInterimTranscript("");
    setSubmitting(true);
    setInterviewerState("thinking");
    setErrorMsg(null);

    try {
      const res = await fetch("http://127.0.0.1:8005/api/interview/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interview_id: interviewId,
          answer: finalAnswer,
        }),
      });

      const json = await res.json();
      if (res.ok) {
        setSession(json.data);
        if (json.data.time_remaining !== undefined) {
          setTimeRemaining(json.data.time_remaining);
        }

        // Auto-speak next question
        const nextQ = json.data.current_question;
        if (nextQ && nextQ.text && json.data.status !== "complete") {
          lastSpokenQIdRef.current = nextQ.id;
          speakQuestionAudio(nextQ.text, nextQ.id);
        } else {
          setInterviewerState("idle");
        }
      } else {
        throw new Error(json.detail || "Failed to submit answer.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Network error. Please try resubmitting.");
      setAnswerText(finalAnswer);
      setInterviewerState("idle");
    } finally {
      setSubmitting(false);
    }
  };

  // 7. Skip Question
  const handleSkipQuestion = async () => {
    if (submitting) return;
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
    stopQuestionAudio();

    setSubmitting(true);
    setInterviewerState("thinking");
    try {
      const res = await fetch("http://127.0.0.1:8005/api/interview/next-question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ interview_id: interviewId }),
      });
      if (res.ok) {
        const json = await res.json();
        setSession(json.data);
        const nextQ = json.data.current_question;
        if (nextQ && nextQ.text) {
          lastSpokenQIdRef.current = nextQ.id;
          speakQuestionAudio(nextQ.text, nextQ.id);
        } else {
          setInterviewerState("idle");
        }
      }
    } catch {
      setInterviewerState("idle");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && !session) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 font-mono text-cyan-300">
        <div className="w-12 h-12 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
        <span className="text-sm tracking-wider uppercase">Calibrating Voice &amp; Assessment Engine...</span>
      </div>
    );
  }

  const currentQ = session?.current_question;
  const isComplete = session?.status === "complete" || timeRemaining <= 0 || session?.current_phase === "complete";
  const history = session?.questions_history || [];
  const activityLog = session?.activity_log || [];

  return (
    <div className="relative z-10 w-full max-w-7xl mx-auto px-4 py-6 flex flex-col gap-6 font-mono">
      {/* ─── Top Control Bar: Active Phase, Timer, & State ─── */}
      <div className="glass-panel p-4 rounded-2xl flex flex-wrap items-center justify-between gap-4 border border-cyan-500/30 shadow-[0_0_30px_rgba(0,240,255,0.15)]">
        {/* Left: Phase & Track Info */}
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-xs font-bold uppercase tracking-wider">
            {session?.domain || "Software Engineering"}
          </span>

          <span className="text-gray-400 text-xs hidden sm:inline">•</span>

          <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-gray-300 text-xs font-bold uppercase tracking-wider">
            Phase: <strong className="text-emerald-400">{session?.current_phase?.replace("_", " ").toUpperCase() || "INTRODUCTION"}</strong>
          </span>

          {/* Difficulty Badge */}
          <span
            className={`px-2.5 py-1 rounded-lg text-xs font-bold uppercase border ${
              session?.difficulty === "hard"
                ? "bg-red-950/60 border-red-500/50 text-red-300"
                : session?.difficulty === "easy"
                ? "bg-emerald-950/60 border-emerald-500/50 text-emerald-300"
                : "bg-amber-950/60 border-amber-500/50 text-amber-300"
            }`}
          >
            Level: {session?.difficulty?.toUpperCase() || "MEDIUM"}
          </span>
        </div>

        {/* Center: Live Synchronized Countdown Timer */}
        <div className="flex items-center gap-2 px-4 py-1.5 rounded-xl bg-slate-950/90 border border-cyan-500/40 text-cyan-300 font-black tracking-widest text-sm shadow-[0_0_15px_rgba(0,240,255,0.2)]">
          <Clock className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span>{formatTimer(timeRemaining)}</span>
          <span className="text-[10px] text-gray-500 font-normal">REMAINING</span>
        </div>

        {/* Right: Exit / Session ID */}
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-gray-500 hidden md:inline">
            ID: {interviewId}
          </span>
          <button
            onClick={onExit}
            className="px-3 py-1 rounded-lg bg-slate-900 border border-slate-700 text-gray-400 hover:text-white transition text-xs"
          >
            Exit Setup
          </button>
        </div>
      </div>

      {/* ─── Main Two-Column Layout ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ─── Left Column (8 cols): Interviewer Avatar Stage & Active Question ─── */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {!isComplete ? (
            <>
              {/* Interviewer Stage Banner */}
              <div className="glass-panel p-6 sm:p-8 rounded-3xl flex flex-col items-center justify-center gap-4 text-center border border-cyan-500/35 relative overflow-hidden shadow-[0_4px_35px_rgba(0,0,0,0.5)]">
                {/* Interviewer Avatar Driven by 4-State Machine */}
                <div className="scale-90">
                  <InterviewerAvatar state={interviewerState} />
                </div>

                {/* State Pill & Audio Indicator */}
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest flex items-center gap-1.5 border transition-all ${
                      interviewerState === "speaking"
                        ? "bg-purple-950/80 border-purple-500/50 text-purple-300 shadow-[0_0_15px_rgba(168,85,247,0.4)]"
                        : interviewerState === "listening"
                        ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.4)]"
                        : interviewerState === "thinking"
                        ? "bg-amber-950/80 border-amber-500/50 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.4)]"
                        : "bg-cyan-950/80 border-cyan-500/50 text-cyan-300 shadow-[0_0_15px_rgba(0,240,255,0.2)]"
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        interviewerState === "speaking"
                          ? "bg-purple-400 animate-ping"
                          : interviewerState === "listening"
                          ? "bg-emerald-400 animate-ping"
                          : interviewerState === "thinking"
                          ? "bg-amber-400 animate-pulse"
                          : "bg-cyan-400"
                      }`}
                    />
                    {interviewerState === "speaking"
                      ? "SPEAKING QUESTION (AUDIO)"
                      : interviewerState === "listening"
                      ? "LISTENING TO CANDIDATE"
                      : interviewerState === "thinking"
                      ? "EVALUATING & ADAPTING"
                      : "READY FOR INPUT"}
                  </span>

                  {currentQ?.category && (
                    <span className="px-2.5 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-xs font-bold uppercase">
                      Category: {currentQ.category}
                    </span>
                  )}
                </div>

                {/* Active Question Box */}
                <motion.div
                  key={currentQ?.id || "q-active"}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="w-full bg-black/60 p-5 sm:p-6 rounded-2xl border border-cyan-500/30 text-left flex flex-col gap-2 shadow-inner"
                >
                  <div className="flex items-center justify-between text-[11px] text-gray-400 border-b border-slate-800 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400 font-bold">
                        {currentQ?.id || "QUESTION 01"}
                      </span>
                      <span className="text-gray-500">•</span>
                      <span className="text-gray-500">
                        {currentQ?.context || "Technical Inquiry"}
                      </span>
                    </div>

                    {/* Question Voice Controls: Play / Replay / Stop */}
                    <button
                      type="button"
                      onClick={() => {
                        if (interviewerState === "speaking") {
                          stopQuestionAudio();
                        } else {
                          speakQuestionAudio(currentQ?.text || "", currentQ?.id);
                        }
                      }}
                      title={interviewerState === "speaking" ? "Stop Audio" : "Replay Question Voice"}
                      className={`px-2.5 py-1 rounded-lg border text-[11px] font-mono transition flex items-center gap-1.5 ${
                        interviewerState === "speaking"
                          ? "bg-purple-500 text-white font-bold border-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.6)]"
                          : "bg-slate-900 border-slate-700 text-gray-300 hover:text-cyan-300"
                      }`}
                    >
                      {interviewerState === "speaking" ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                      <span>{interviewerState === "speaking" ? "Stop Voice" : "Replay Voice"}</span>
                    </button>
                  </div>

                  <p className="text-sm sm:text-base text-gray-100 font-sans leading-relaxed pt-1 font-medium">
                    {currentQ?.text || "Please introduce yourself and discuss your core technical projects."}
                  </p>
                </motion.div>
              </div>

              {/* ─── Real-Time Voice & Text Candidate Response Area ─── */}
              <form
                onSubmit={handleSubmitAnswer}
                className={`glass-panel p-5 rounded-2xl flex flex-col gap-3 border transition-all duration-300 shadow-lg ${
                  isListening
                    ? "border-emerald-400 shadow-[0_0_35px_rgba(16,185,129,0.3)] bg-slate-950/95"
                    : "border-cyan-500/25"
                }`}
              >
                {/* Header with Live Voice Toggle */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <label className="text-gray-300 font-bold flex items-center gap-1.5">
                      <span>Your Technical Response:</span>
                    </label>

                    {/* Live Voice Status Pill */}
                    {isListening && (
                      <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-500/50 text-emerald-300 text-[10px] animate-pulse">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                        <span>LIVE VOICE TRANSCRIBING</span>
                      </span>
                    )}
                  </div>

                  {/* Mic Button in Header */}
                  <button
                    type="button"
                    onClick={toggleListening}
                    className={`px-3 py-1 rounded-xl text-xs font-mono font-bold transition-all flex items-center gap-1.5 ${
                      isListening
                        ? "bg-red-500 text-white shadow-[0_0_20px_rgba(239,68,68,0.7)] animate-pulse"
                        : "bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/80 shadow-[0_0_12px_rgba(16,185,129,0.2)]"
                    }`}
                  >
                    {isListening ? (
                      <>
                        <MicOff className="w-3.5 h-3.5" />
                        <span>Stop Mic</span>
                      </>
                    ) : (
                      <>
                        <Mic className="w-3.5 h-3.5" />
                        <span>Speak (Voice Input)</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Textarea with Real-Time Reflection */}
                <div className="relative">
                  <textarea
                    value={answerText + (interimTranscript ? (answerText.length > 0 && !answerText.endsWith(" ") ? " " : "") + interimTranscript : "")}
                    onChange={(e) => setAnswerText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault();
                        handleSubmitAnswer();
                      }
                    }}
                    disabled={submitting}
                    rows={6}
                    placeholder={
                      isListening
                        ? "🎙️ Listening to your speech in real time... Speak clearly into your microphone."
                        : "Type or click 'Speak' to answer by voice. Be specific about technologies, architecture, and tradeoffs..."
                    }
                    className={`w-full bg-slate-950/90 rounded-xl p-4 text-xs sm:text-sm font-sans text-gray-100 placeholder-gray-500 focus:outline-none leading-relaxed transition-all border ${
                      isListening
                        ? "border-emerald-400/80 bg-black/80 ring-2 ring-emerald-500/20"
                        : "border-cyan-500/30 focus:border-cyan-400"
                    }`}
                  />

                  {/* Inline Audio Waveform Canvas overlay while speaking or listening */}
                  <AnimatePresence>
                    {(isListening || interviewerState === "speaking") && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute top-3 right-4 pointer-events-none flex items-center gap-2 bg-slate-950/90 px-3 py-1 rounded-xl border border-cyan-500/40 backdrop-blur-md shadow-md"
                      >
                        <canvas
                          ref={waveCanvasRef}
                          width={80}
                          height={20}
                          className="rounded"
                        />
                        <span className="text-[10px] text-gray-300 font-mono">
                          {isListening ? "Listening..." : "Audio Active"}
                        </span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {errorMsg && (
                  <div className="text-red-400 text-xs font-mono">{errorMsg}</div>
                )}

                {/* Bottom Actions Toolbar */}
                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={handleSkipQuestion}
                      disabled={submitting}
                      className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-gray-400 hover:text-white transition flex items-center gap-1.5 text-xs"
                    >
                      <SkipForward className="w-3.5 h-3.5" />
                      <span>Skip Question</span>
                    </button>

                    <span className="text-gray-500 text-[11px] hidden sm:inline">
                      Press <strong className="text-cyan-400">Ctrl+Enter</strong> or click Submit
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Primary Voice Mic Button */}
                    <button
                      type="button"
                      onClick={toggleListening}
                      disabled={submitting}
                      className={`p-2.5 rounded-xl transition flex items-center justify-center ${
                        isListening
                          ? "bg-red-500 text-white shadow-[0_0_20px_rgba(239,68,68,0.8)] animate-pulse"
                          : "bg-emerald-950 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-900 shadow-[0_0_12px_rgba(16,185,129,0.2)]"
                      }`}
                      title={isListening ? "Stop Voice Input" : "Start Voice Input"}
                    >
                      {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    </button>

                    {/* Submit Button */}
                    <button
                      type="submit"
                      disabled={submitting || (!answerText.trim() && !interimTranscript.trim())}
                      className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-black font-bold text-xs font-mono uppercase tracking-wider hover:brightness-110 disabled:opacity-40 transition shadow-[0_0_20px_rgba(0,240,255,0.4)] flex items-center gap-2"
                    >
                      {submitting ? (
                        <>
                          <div className="w-3.5 h-3.5 rounded-full border-2 border-black border-t-transparent animate-spin" />
                          <span>Evaluating...</span>
                        </>
                      ) : (
                        <>
                          <span>Submit Response</span>
                          <Send className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </form>
            </>
          ) : (
            /* ─── Interview Complete State ─── */
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-panel p-8 rounded-3xl flex flex-col items-center justify-center text-center gap-6 border border-emerald-500/50 shadow-[0_0_50px_rgba(16,185,129,0.25)]"
            >
              <div className="w-16 h-16 rounded-full bg-emerald-950/80 border border-emerald-500/60 flex items-center justify-center text-emerald-400 shadow-[0_0_25px_rgba(16,185,129,0.5)]">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div className="flex flex-col gap-2">
                <span className="text-[10px] font-mono uppercase tracking-widest text-emerald-400">
                  PROTOCOL SESSION CONCLUDED
                </span>
                <h2 className="text-2xl font-black text-cyan-200">
                  Interview Assessment Complete
                </h2>
                <p className="text-xs text-gray-300 max-w-lg leading-relaxed font-sans">
                  You have completed the technical question rounds. All responses, transcripts, and evaluations have been safely stored in the session log.
                </p>
              </div>

              {/* Turn count summary */}
              <div className="grid grid-cols-2 gap-4 text-xs font-mono w-full max-w-md">
                <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 flex flex-col gap-1">
                  <span className="text-gray-400 text-[10px]">QUESTIONS COMPLETED</span>
                  <span className="text-emerald-300 font-bold text-base">{history.length}</span>
                </div>
                <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 flex flex-col gap-1">
                  <span className="text-gray-400 text-[10px]">FINAL DIFFICULTY</span>
                  <span className="text-cyan-300 font-bold text-base">{session?.difficulty?.toUpperCase()}</span>
                </div>
              </div>

              <button
                onClick={onExit}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-black font-bold text-xs uppercase tracking-wider hover:brightness-110 transition shadow-[0_0_20px_rgba(0,240,255,0.4)]"
              >
                Return to Protocol Setup
              </button>
            </motion.div>
          )}

          {/* ─── Turn History Accordion ─── */}
          {history.length > 0 && (
            <div className="glass-panel rounded-2xl border border-cyan-500/20 overflow-hidden">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="w-full p-4 flex items-center justify-between text-xs text-cyan-300 hover:bg-slate-900/50 transition font-bold"
              >
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-cyan-400" />
                  <span>Turn History &amp; Evaluation Trace ({history.length} Turns)</span>
                </div>
                {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              <AnimatePresence>
                {showHistory && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="p-4 border-t border-slate-800 space-y-4 max-h-96 overflow-y-auto"
                  >
                    {history.map((h: any, idx: number) => (
                      <div
                        key={idx}
                        className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 flex flex-col gap-2 text-xs"
                      >
                        <div className="flex items-center justify-between text-[10px] text-gray-500">
                          <span className="text-cyan-400 font-bold">TURN 0{idx + 1} • {h.category}</span>
                          <span>{h.timestamp}</span>
                        </div>
                        <p className="text-gray-300 font-sans font-medium">Q: {h.question_text}</p>
                        <p className="text-gray-400 font-sans italic bg-black/40 p-2.5 rounded-lg border border-slate-900">
                          A: {h.answer_text}
                        </p>
                        {h.evaluation && (
                          <div className="text-[11px] text-emerald-400 font-mono flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                            <span>AI Evaluation: {h.evaluation}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* ─── Right Column (4 cols): Agentic Activity Stream ─── */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          <div className="glass-panel p-4 rounded-2xl flex flex-col gap-3 border border-cyan-500/25 shadow-[0_4px_25px_rgba(0,0,0,0.4)]">
            <div className="flex items-center justify-between border-b border-cyan-500/15 pb-2.5">
              <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
                Live Activity Stream
              </span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>

            {/* Event List */}
            <div
              ref={activityScrollRef}
              className="space-y-2.5 max-h-[520px] overflow-y-auto pr-1 text-xs"
            >
              {activityLog.length === 0 ? (
                <div className="text-center py-12 text-gray-600 text-[11px]">
                  Activity events will stream here in real time...
                </div>
              ) : (
                activityLog.map((ev: any, i: number) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col gap-1 text-[11px]"
                  >
                    <div className="flex items-center justify-between text-gray-500 text-[10px]">
                      <span className="text-cyan-400 font-bold">{ev.event}</span>
                      <span>{ev.timestamp}</span>
                    </div>
                    {ev.details && (
                      <p className="text-gray-300 font-sans text-[11px] leading-relaxed">
                        {ev.details}
                      </p>
                    )}
                  </motion.div>
                ))
              )}
            </div>

            <div className="pt-2 border-t border-cyan-500/10 text-[10px] text-gray-500 text-center">
              Adaptive Voice &amp; Evaluation Engine Active
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
