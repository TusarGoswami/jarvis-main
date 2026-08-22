"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail,
  Send,
  AppWindow,
  Search,
  Terminal,
  X,
  Sparkles,
  CheckCircle2,
  Cpu,
  ChevronRight,
  ShieldCheck
} from "lucide-react";

interface ActionCenterProps {
  onExecuteCommand: (query: string) => void;
}

export const ActionCenter: React.FC<ActionCenterProps> = ({ onExecuteCommand }) => {
  const [activeModal, setActiveModal] = useState<"email" | "app" | "search" | "terminal" | null>(null);

  // Email form state
  const [emailTo, setEmailTo] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");

  // App launch state
  const [appName, setAppName] = useState("notepad");
  const [appText, setAppText] = useState("");

  // Search state
  const [searchQuery, setSearchQuery] = useState("");

  // Terminal/File task state
  const [terminalTask, setTerminalTask] = useState("");

  const handleSendEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailTo.trim()) return;
    const query = `send an email to ${emailTo.trim()} with subject "${emailSubject.trim() || 'Message from Vocalis AI'}" saying ${emailBody.trim() || 'Hello from Vocalis AI'}`;
    onExecuteCommand(query);
    setActiveModal(null);
    setEmailTo("");
    setEmailSubject("");
    setEmailBody("");
  };

  const handleAppLaunchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!appName.trim()) return;
    let query = `open ${appName.trim()}`;
    if (appText.trim()) {
      query += ` and write ${appText.trim()}`;
    }
    onExecuteCommand(query);
    setActiveModal(null);
    setAppText("");
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    onExecuteCommand(`search for ${searchQuery.trim()}`);
    setActiveModal(null);
    setSearchQuery("");
  };

  const handleTerminalSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!terminalTask.trim()) return;
    onExecuteCommand(terminalTask.trim());
    setActiveModal(null);
    setTerminalTask("");
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 mt-2 mb-24">
      {/* Quick Action Grid Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span className="text-xs font-mono font-bold tracking-wider text-cyan-300 uppercase">
            Action Mode — Assignable Autonomous Tasks
          </span>
        </div>
        <span className="text-[10px] font-mono text-gray-500">1-Click Dispatch & Voice Enabled</span>
      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {/* Email Dispatch Card */}
        <motion.div
          whileHover={{ scale: 1.02, y: -2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setActiveModal("email")}
          className="p-3.5 rounded-2xl glass-panel border border-cyan-500/30 hover:border-cyan-400/60 bg-gradient-to-b from-cyan-950/40 to-slate-950/80 cursor-pointer transition-all shadow-[0_4px_20px_rgba(0,0,0,0.4)] group flex flex-col justify-between"
        >
          <div>
            <div className="w-8 h-8 rounded-xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-300 mb-2.5 group-hover:bg-cyan-500 group-hover:text-black transition-all">
              <Mail className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-gray-100 mb-1 group-hover:text-cyan-300 transition">
              Send Email
            </h3>
            <p className="text-[11px] text-gray-400 leading-tight">
              Draft & dispatch emails securely via Gmail API.
            </p>
          </div>
          <div className="flex items-center justify-between mt-3 pt-2 border-t border-cyan-500/10 text-[10px] font-mono text-cyan-400">
            <span>Assign Task</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </motion.div>

        {/* App Launcher Card */}
        <motion.div
          whileHover={{ scale: 1.02, y: -2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setActiveModal("app")}
          className="p-3.5 rounded-2xl glass-panel border border-blue-500/30 hover:border-blue-400/60 bg-gradient-to-b from-blue-950/40 to-slate-950/80 cursor-pointer transition-all shadow-[0_4px_20px_rgba(0,0,0,0.4)] group flex flex-col justify-between"
        >
          <div>
            <div className="w-8 h-8 rounded-xl bg-blue-500/20 border border-blue-400/40 flex items-center justify-center text-blue-300 mb-2.5 group-hover:bg-blue-500 group-hover:text-black transition-all">
              <AppWindow className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-gray-100 mb-1 group-hover:text-blue-300 transition">
              Launch & Automate
            </h3>
            <p className="text-[11px] text-gray-400 leading-tight">
              Open apps, type notes, and trigger GUI workflows.
            </p>
          </div>
          <div className="flex items-center justify-between mt-3 pt-2 border-t border-blue-500/10 text-[10px] font-mono text-blue-400">
            <span>Assign Task</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </motion.div>

        {/* Web Intelligence Card */}
        <motion.div
          whileHover={{ scale: 1.02, y: -2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setActiveModal("search")}
          className="p-3.5 rounded-2xl glass-panel border border-purple-500/30 hover:border-purple-400/60 bg-gradient-to-b from-purple-950/40 to-slate-950/80 cursor-pointer transition-all shadow-[0_4px_20px_rgba(0,0,0,0.4)] group flex flex-col justify-between"
        >
          <div>
            <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-400/40 flex items-center justify-center text-purple-300 mb-2.5 group-hover:bg-purple-500 group-hover:text-black transition-all">
              <Search className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-gray-100 mb-1 group-hover:text-purple-300 transition">
              Web Intelligence
            </h3>
            <p className="text-[11px] text-gray-400 leading-tight">
              Real-time web search, summaries & scraping.
            </p>
          </div>
          <div className="flex items-center justify-between mt-3 pt-2 border-t border-purple-500/10 text-[10px] font-mono text-purple-400">
            <span>Assign Task</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </motion.div>

        {/* Multi-Step ReAct Agent Card */}
        <motion.div
          whileHover={{ scale: 1.02, y: -2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setActiveModal("terminal")}
          className="p-3.5 rounded-2xl glass-panel border border-emerald-500/30 hover:border-emerald-400/60 bg-gradient-to-b from-emerald-950/40 to-slate-950/80 cursor-pointer transition-all shadow-[0_4px_20px_rgba(0,0,0,0.4)] group flex flex-col justify-between"
        >
          <div>
            <div className="w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center text-emerald-300 mb-2.5 group-hover:bg-emerald-500 group-hover:text-black transition-all">
              <Terminal className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-bold text-gray-100 mb-1 group-hover:text-emerald-300 transition">
              Multi-Step Agent
            </h3>
            <p className="text-[11px] text-gray-400 leading-tight">
              Write code, run scripts & verify disk outcomes.
            </p>
          </div>
          <div className="flex items-center justify-between mt-3 pt-2 border-t border-emerald-500/10 text-[10px] font-mono text-emerald-400">
            <span>Assign Task</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </motion.div>
      </div>

      {/* ─── Task Modals ─── */}
      <AnimatePresence>
        {/* Email Task Modal */}
        {activeModal === "email" && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-lg glass-panel rounded-2xl border border-cyan-500/30 p-5 shadow-[0_0_40px_rgba(0,240,255,0.2)]"
            >
              <div className="flex items-center justify-between mb-4 border-b border-cyan-500/20 pb-3">
                <div className="flex items-center gap-2 text-cyan-300 font-bold text-sm font-mono">
                  <Mail className="w-4 h-4" />
                  <span>Assign Email Dispatch Task</span>
                </div>
                <button
                  onClick={() => setActiveModal(null)}
                  className="p-1 rounded-lg text-gray-400 hover:text-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleSendEmailSubmit} className="space-y-3 font-mono text-xs">
                <div>
                  <label className="block text-gray-400 text-[11px] mb-1">RECIPIENT EMAIL (TO):</label>
                  <input
                    type="email"
                    required
                    placeholder="colleague@example.com"
                    value={emailTo}
                    onChange={(e) => setEmailTo(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-cyan-400"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-[11px] mb-1">SUBJECT:</label>
                  <input
                    type="text"
                    placeholder="Project Status Update"
                    value={emailSubject}
                    onChange={(e) => setEmailSubject(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-cyan-400"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-[11px] mb-1">MESSAGE BODY:</label>
                  <textarea
                    rows={4}
                    placeholder="Hi, here are the updates from Vocalis AI..."
                    value={emailBody}
                    onChange={(e) => setEmailBody(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-cyan-400 resize-none font-sans"
                  />
                </div>

                <div className="flex items-center gap-1 text-[10px] text-cyan-400/80 bg-cyan-950/40 p-2 rounded-lg border border-cyan-500/20">
                  <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>Human-in-the-loop confirmation will verify before dispatch.</span>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setActiveModal(null)}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-gray-300 hover:bg-slate-700 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-black font-bold hover:brightness-110 shadow-[0_0_15px_rgba(0,240,255,0.4)] transition flex items-center gap-1.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Dispatch Email Task</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {/* App Launcher Modal */}
        {activeModal === "app" && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-lg glass-panel rounded-2xl border border-blue-500/30 p-5 shadow-[0_0_40px_rgba(59,130,246,0.2)]"
            >
              <div className="flex items-center justify-between mb-4 border-b border-blue-500/20 pb-3">
                <div className="flex items-center gap-2 text-blue-300 font-bold text-sm font-mono">
                  <AppWindow className="w-4 h-4" />
                  <span>Assign App & GUI Automation Task</span>
                </div>
                <button
                  onClick={() => setActiveModal(null)}
                  className="p-1 rounded-lg text-gray-400 hover:text-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleAppLaunchSubmit} className="space-y-3 font-mono text-xs">
                <div>
                  <label className="block text-gray-400 text-[11px] mb-1">APPLICATION TO LAUNCH:</label>
                  <select
                    value={appName}
                    onChange={(e) => setAppName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-400"
                  >
                    <option value="notepad">Notepad</option>
                    <option value="calculator">Calculator</option>
                    <option value="chrome">Google Chrome / Browser</option>
                    <option value="cmd">Command Prompt (Terminal)</option>
                    <option value="vscode">VS Code / Workspace</option>
                  </select>
                </div>

                <div>
                  <label className="block text-gray-400 text-[11px] mb-1">AUTOMATED TEXT TO TYPE (OPTIONAL):</label>
                  <textarea
                    rows={3}
                    placeholder="Text to type automatically into the window..."
                    value={appText}
                    onChange={(e) => setAppText(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-blue-400 resize-none font-sans"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setActiveModal(null)}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-gray-300 hover:bg-slate-700 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold hover:brightness-110 shadow-[0_0_15px_rgba(59,130,246,0.4)] transition flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Execute App Task</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {/* Web Search Modal */}
        {activeModal === "search" && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-lg glass-panel rounded-2xl border border-purple-500/30 p-5 shadow-[0_0_40px_rgba(168,85,247,0.2)]"
            >
              <div className="flex items-center justify-between mb-4 border-b border-purple-500/20 pb-3">
                <div className="flex items-center gap-2 text-purple-300 font-bold text-sm font-mono">
                  <Search className="w-4 h-4" />
                  <span>Assign Web Intelligence Task</span>
                </div>
                <button
                  onClick={() => setActiveModal(null)}
                  className="p-1 rounded-lg text-gray-400 hover:text-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleSearchSubmit} className="space-y-3 font-mono text-xs">
                <div>
                  <label className="block text-gray-400 text-[11px] mb-1">SEARCH QUERY OR RESEARCH TOPIC:</label>
                  <input
                    type="text"
                    required
                    placeholder="Latest breakthroughs in AI multimodal agents"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-purple-400"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setActiveModal(null)}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-gray-300 hover:bg-slate-700 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-600 text-white font-bold hover:brightness-110 shadow-[0_0_15px_rgba(168,85,247,0.4)] transition flex items-center gap-1.5"
                  >
                    <Search className="w-3.5 h-3.5" />
                    <span>Run Web Research</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {/* Multi-step Agent Modal */}
        {activeModal === "terminal" && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-lg glass-panel rounded-2xl border border-emerald-500/30 p-5 shadow-[0_0_40px_rgba(16,185,129,0.2)]"
            >
              <div className="flex items-center justify-between mb-4 border-b border-emerald-500/20 pb-3">
                <div className="flex items-center gap-2 text-emerald-300 font-bold text-sm font-mono">
                  <Terminal className="w-4 h-4" />
                  <span>Assign Multi-Step Autonomous Task</span>
                </div>
                <button
                  onClick={() => setActiveModal(null)}
                  className="p-1 rounded-lg text-gray-400 hover:text-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleTerminalSubmit} className="space-y-3 font-mono text-xs">
                <div>
                  <label className="block text-gray-400 text-[11px] mb-1">TASK OBJECTIVE (PLAN - ACT - OBSERVE - VERIFY):</label>
                  <textarea
                    rows={3}
                    required
                    placeholder="Create a python script named test_calc.py that calculates fibonacci series and run it"
                    value={terminalTask}
                    onChange={(e) => setTerminalTask(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-400 resize-none font-sans"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setActiveModal(null)}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-gray-300 hover:bg-slate-700 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-black font-bold hover:brightness-110 shadow-[0_0_15px_rgba(16,185,129,0.4)] transition flex items-center gap-1.5"
                  >
                    <Cpu className="w-3.5 h-3.5" />
                    <span>Launch ReAct Orchestrator</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
