"use client";

// ─── Shared Types for Vocalis AI Frontend ───

export type AssistantState = "idle" | "listening" | "thinking" | "speaking" | "tool_use";

export interface MessageItem {
  id: string;
  sender: "user" | "vocalis";
  text: string;
  timestamp: string;
  language?: string;
  confidence?: number;
  intent?: string;
  actionsExecuted?: Array<{ status: string; action: string; target?: string; query?: string }>;
  needsConfirmation?: boolean;
  confirmationReason?: string;
  citations?: string[];
  latencyMs?: number;
}

export interface SystemStats {
  cpu_percent: number;
  ram_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  disks: Record<string, number>;
  net_sent_mb: number;
  net_recv_mb: number;
  battery: number | null;
  timestamp?: number;
}

// State visual configuration map — carries forward ArcReactor color scheme
export const STATE_CONFIG: Record<
  AssistantState,
  {
    label: string;
    color: string;        // primary CSS color
    glowRgb: string;      // for rgba() usage
    ringColor: string;    // SVG stroke
    speed: number;        // animation speed multiplier
    particleIntensity: number; // 0-1
  }
> = {
  idle: {
    label: "Ready",
    color: "#00f0ff",
    glowRgb: "0, 240, 255",
    ringColor: "#00f0ff",
    speed: 1,
    particleIntensity: 0.3,
  },
  listening: {
    label: "Listening",
    color: "#10b981",
    glowRgb: "16, 185, 129",
    ringColor: "#10b981",
    speed: 2,
    particleIntensity: 0.6,
  },
  thinking: {
    label: "Thinking",
    color: "#f59e0b",
    glowRgb: "245, 158, 11",
    ringColor: "#f59e0b",
    speed: 3,
    particleIntensity: 0.5,
  },
  speaking: {
    label: "Speaking",
    color: "#a855f7",
    glowRgb: "168, 85, 247",
    ringColor: "#a855f7",
    speed: 2.5,
    particleIntensity: 0.7,
  },
  tool_use: {
    label: "Executing",
    color: "#06b6d4",
    glowRgb: "6, 182, 212",
    ringColor: "#06b6d4",
    speed: 3.5,
    particleIntensity: 0.8,
  },
};
