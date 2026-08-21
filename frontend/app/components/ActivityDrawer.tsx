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
 * ActivityDrawer — Slide-in right panel for chat/action history.
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
        className="fixed right-4 top-1/2 -translate-y-1/2 z-30 p-3 rounded-xl glass-panel-glow text-cyan-300 hover:text-cyan-100 transition-colors"
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
              className="fixed inset-0 bg-black/30 backdrop-blur-sm z-30"
            />

            {/* Panel */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed right-0 top-0 bottom-0 w-[380px] max-w-[90vw] z-40 flex flex-col glass-panel border-l border-cyan-500/20"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-cyan-500/20">
                <span className="font-mono text-xs uppercase tracking-widest text-cyan-400 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
                  Activity Stream
                </span>
                <button
                  onClick={onToggle}
                  className="p-1.5 rounded-lg hover:bg-slate-800 text-gray-400 hover:text-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Messages */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
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
