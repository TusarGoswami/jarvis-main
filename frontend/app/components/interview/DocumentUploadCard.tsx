"use client";
/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Edit3,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { getApiUrl } from "../../lib/api";

interface DocumentUploadCardProps {
  title: string;
  subtitle: string;
  type: "cv" | "jd";
  endpoint: string;
  onExtracted: (data: any) => void;
  extractedData: any | null;
}

export const DocumentUploadCard: React.FC<DocumentUploadCardProps> = ({
  title,
  subtitle,
  type,
  endpoint,
  onExtracted,
  extractedData,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTextMode, setIsTextMode] = useState(false);
  const [rawText, setRawText] = useState("");
  const [showDetails, setShowDetails] = useState(true);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processUpload = async (file?: File, text?: string) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      if (file) {
        formData.append("file", file);
        setUploadedFilename(file.name);
      } else if (text) {
        formData.append("raw_text", text);
        setUploadedFilename("Pasted Text Input");
      } else {
        throw new Error("No file or text provided.");
      }

      const res = await fetch(getApiUrl(endpoint), {
        method: "POST",
        body: formData,
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || "Document extraction failed.");
      }

      onExtracted(json.data);
    } catch (err: any) {
      setError(err.message || "Failed to process document. Please retry with a valid file.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processUpload(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processUpload(file);
    }
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawText.trim()) return;
    processUpload(undefined, rawText);
  };

  return (
    <div className="glass-panel p-5 rounded-2xl flex flex-col gap-4 border border-cyan-500/25 shadow-[0_4px_25px_rgba(0,0,0,0.4)]">
      {/* Card Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/15 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold font-mono text-cyan-300 uppercase tracking-wider">
              {title}
            </h3>
            <p className="text-[11px] text-gray-400 font-mono">{subtitle}</p>
          </div>
        </div>

        {/* Text/File Toggle */}
        <button
          type="button"
          onClick={() => {
            setIsTextMode(!isTextMode);
            setError(null);
          }}
          className="text-[10px] font-mono px-2 py-1 rounded bg-slate-900 border border-slate-700 text-gray-300 hover:text-cyan-300 transition flex items-center gap-1"
        >
          <Edit3 className="w-3 h-3" />
          <span>{isTextMode ? "File Upload" : "Paste Text"}</span>
        </button>
      </div>

      {/* Upload Zone or Extracted Confirmation Display */}
      {!extractedData ? (
        <>
          {!isTextMode ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center gap-2.5 cursor-pointer transition-all ${
                isDragging
                  ? "border-cyan-400 bg-cyan-500/10 shadow-[0_0_20px_rgba(0,240,255,0.3)]"
                  : "border-cyan-500/30 bg-slate-950/60 hover:border-cyan-400/60 hover:bg-slate-900/60"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.txt,.md"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="w-10 h-10 rounded-full bg-cyan-950 border border-cyan-500/40 flex items-center justify-center text-cyan-300 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                {loading ? (
                  <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
                ) : (
                  <Upload className="w-5 h-5" />
                )}
              </div>
              <div className="text-center font-mono">
                <span className="text-xs font-bold text-cyan-200">
                  {loading ? "PARSING & EXTRACTING..." : "DROP YOUR FILE HERE"}
                </span>
                <p className="text-[10px] text-gray-400 mt-0.5">
                  Supported formats: PDF, DOCX, TXT
                </p>
              </div>
              <button
                type="button"
                className="mt-1 px-3 py-1 bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 rounded-lg text-xs font-mono hover:bg-cyan-900/80 transition"
              >
                Select File
              </button>
            </div>
          ) : (
            <form onSubmit={handleTextSubmit} className="flex flex-col gap-2">
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder={`Paste your ${type === "cv" ? "Resume / CV" : "Job Description"} content here...`}
                rows={5}
                className="w-full bg-slate-950/80 border border-cyan-500/30 rounded-xl p-3 text-xs font-mono text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-400 leading-relaxed"
              />
              <button
                type="submit"
                disabled={loading || !rawText.trim()}
                className="self-end px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-black text-xs font-mono font-bold hover:brightness-110 disabled:opacity-40 transition flex items-center gap-1.5"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Extracting...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Parse Text</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* Error Banner */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 rounded-xl bg-red-950/60 border border-red-500/40 flex items-start gap-2 text-xs font-mono text-red-300"
            >
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <span>{error}</span>
              </div>
            </motion.div>
          )}
        </>
      ) : (
        /* Extracted Profile / JD Confirmation View */
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-slate-950/80 border border-emerald-500/40 rounded-xl p-4 flex flex-col gap-3 font-mono text-xs shadow-[0_0_25px_rgba(16,185,129,0.15)]"
        >
          {/* Status Banner */}
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2 text-emerald-400 font-bold">
              <CheckCircle2 className="w-4 h-4" />
              <span>
                {type === "cv" ? "CANDIDATE PROFILE GENERATED" : "JOB SPECIFICATION PARSED"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onExtracted(null)}
                className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-gray-400 hover:text-white transition"
              >
                Re-upload
              </button>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-gray-400 hover:text-cyan-300"
              >
                {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Quick Summary Pill */}
          <div className="flex items-center gap-2 text-[11px] text-gray-300">
            <span className="font-bold text-cyan-300">
              {type === "cv" ? extractedData.name || "Candidate" : extractedData.title || "Target Role"}
            </span>
            <span>•</span>
            <span className="text-gray-400">
              {type === "cv"
                ? extractedData.experience_years || "Experience Ready"
                : extractedData.inferred_domain || "Software Engineering"}
            </span>
            {uploadedFilename && (
              <span className="text-[10px] text-gray-500 ml-auto truncate max-w-[150px]">
                ({uploadedFilename})
              </span>
            )}
          </div>

          {/* Expandable Details */}
          <AnimatePresence>
            {showDetails && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="flex flex-col gap-2.5 pt-1 overflow-hidden"
              >
                {/* Summary / Responsibilities */}
                {extractedData.summary && (
                  <p className="text-[11px] text-gray-300 italic bg-black/40 p-2.5 rounded-lg border border-slate-800">
                    &ldquo;{extractedData.summary}&rdquo;
                  </p>
                )}

                {/* Skills Chips */}
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider">
                    {type === "cv" ? "Extracted Technical Skills" : "Required Core Skills"}
                  </span>
                  <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-1">
                    {(type === "cv"
                      ? extractedData.skills || []
                      : extractedData.required_skills || []
                    ).map((skill: string, i: number) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded-full bg-cyan-950/70 border border-cyan-500/40 text-cyan-300 text-[10px]"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Frameworks & Languages */}
                {((extractedData.languages && extractedData.languages.length > 0) ||
                  (extractedData.frameworks && extractedData.frameworks.length > 0)) && (
                  <div className="flex items-center gap-1.5 text-[10px] text-gray-400 flex-wrap">
                    <span className="text-gray-500">Stacks:</span>
                    {(extractedData.languages || []).concat(extractedData.frameworks || []).map((tech: string, i: number) => (
                      <span key={i} className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-gray-300">
                        {tech}
                      </span>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </div>
  );
};
