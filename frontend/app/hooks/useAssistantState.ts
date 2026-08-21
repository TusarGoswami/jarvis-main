"use client";

import { createContext, useContext } from "react";
import type { AssistantState } from "../components/types";

export interface AssistantContextValue {
  state: AssistantState;
  audioAmplitude: number;
  transcript: string;
  isConnected: boolean;
  devOverride: AssistantState | null;
  setDevOverride: (s: AssistantState | null) => void;
  setDevAmplitude: (a: number) => void;
}

const defaultValue: AssistantContextValue = {
  state: "idle",
  audioAmplitude: 0,
  transcript: "",
  isConnected: false,
  devOverride: null,
  setDevOverride: () => {},
  setDevAmplitude: () => {},
};

export const AssistantContext = createContext<AssistantContextValue>(defaultValue);

export function useAssistantState() {
  return useContext(AssistantContext);
}
