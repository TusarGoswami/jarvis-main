"use client";

import React, { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Activity, MessageSquare } from "lucide-react";
import { ActionFeed } from "./ActionFeed";
import type { MessageItem } from "./types";

interface ActivityDrawerProps {
  isOpen: boolean;
  onToggle: () => void;
  messages: MessageItem[];
  onConfirmAction: (messageId: string) => void;
  onCancelAction: (messageId: string) => void;
  onPlayAudio?: (text: string, lang?: string) => void;
  unreadCount: number;
}

/**
 * ActivityDrawer — Slide-in right panel for chat and action history.
 * Collapsed by default in voice-first mode. Toggle button sits at right edge.
 */
export const ActivityDrawer: React.FC<ActivityDrawerProps> = ({
  isOpen,
  onToggle,
  messages,
  onConfirmAction,
  onCancelAction,
  onPlayAudio,
  unreadCount,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, isOpen]);

  return (
    <>
      {/* Toggle button — fixed at right edge */}
      <motion.button
        onClick={onToggle}
        className="fixed right-4 top-1/2 -translate-y-1/2 z-30 p-3 rounded-xl glass-panel-glow text-cyan-300 hover:text-cyan-100 transition-colors shadow-[0_0_20px_rgba(0,240,255,0.2)]"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        title="Toggle activity stream"
      >
        <MessageSquare className="w-5 h-5" />
        {unreadCount > 0 && !isOpen && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center"
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </motion.span>
        )}
      </motion.button>

      {/* Drawer panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onToggle}
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-30"
            />

            {/* Panel */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed right-0 top-0 bottom-0 w-[440px] max-w-[92vw] z-40 flex flex-col glass-panel border-l border-cyan-500/20 shadow-[0_0_50px_rgba(0,0,0,0.8)]"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-3.5 border-b border-cyan-500/20">
                <div className="flex items-center gap-2 px-2 text-xs font-mono font-bold text-cyan-300">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <span>Activity Stream</span>
                </div>

                <button
                  onClick={onToggle}
                  className="p-1.5 rounded-lg hover:bg-slate-800 text-gray-400 hover:text-white transition cursor-pointer"
                  title="Close drawer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Content body */}
              <div className="flex-1 overflow-y-auto p-4 flex flex-col" ref={scrollRef}>
                <ActionFeed
                  messages={messages}
                  onConfirmAction={onConfirmAction}
                  onCancelAction={onCancelAction}
                  onPlayAudio={onPlayAudio}
                />
              </div>

              {/* Footer info */}
              <div className="px-4 py-2 border-t border-cyan-500/10 text-[10px] font-mono text-gray-500 text-center">
                Confidence &amp; Safety Guardrails Enabled
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};
