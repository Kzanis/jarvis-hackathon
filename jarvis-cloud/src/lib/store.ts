/**
 * State machine globale de l'interface Jarvis (zustand).
 *
 * États de l'avatar HUD :
 *  - idle       : Jarvis attend
 *  - listening  : micro actif (Whisper STT en cours côté backend)
 *  - thinking   : Claude réfléchit (slow-path LLM)
 *  - speaking   : TTS en lecture (lip-sync amplitude audio)
 *  - action     : exécution confirmée (flash vert bref)
 *  - error      : flash orange + ondulation perturbée
 */

import { create } from "zustand";

import type { JarvisResponse } from "./jarvis-api";

export type JarvisState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "action"
  | "error";

export interface TranscriptEntry {
  role: "user" | "jarvis";
  content: string;
  timestamp: number;
}

interface JarvisStore {
  state: JarvisState;
  transcript: TranscriptEntry[];
  lastResponse: JarvisResponse | null;
  lastError: string | null;

  setState: (s: JarvisState) => void;
  pushUser: (content: string) => void;
  pushJarvis: (content: string) => void;
  setResponse: (r: JarvisResponse) => void;
  setError: (e: string | null) => void;
  reset: () => void;
}

export const useJarvis = create<JarvisStore>((set) => ({
  state: "idle",
  transcript: [],
  lastResponse: null,
  lastError: null,

  setState: (s) => set({ state: s }),
  pushUser: (content) =>
    set((store) => ({
      transcript: [
        ...store.transcript,
        { role: "user", content, timestamp: Date.now() },
      ],
    })),
  pushJarvis: (content) =>
    set((store) => ({
      transcript: [
        ...store.transcript,
        { role: "jarvis", content, timestamp: Date.now() },
      ],
    })),
  setResponse: (r) => set({ lastResponse: r, lastError: null }),
  setError: (e) => set({ lastError: e, state: e ? "error" : "idle" }),
  reset: () =>
    set({ state: "idle", transcript: [], lastResponse: null, lastError: null }),
}));
