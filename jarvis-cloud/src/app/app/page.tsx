"use client";

import { AvatarHUD } from "@/components/AvatarHUD";
import { CommandComposer } from "@/components/CommandComposer";
import { Transcript } from "@/components/Transcript";
import { useJarvis } from "@/lib/store";

const STATE_LABELS: Record<string, string> = {
  idle: "À votre service, Monsieur.",
  listening: "Je vous écoute…",
  thinking: "Permettez-moi un instant…",
  speaking: "Jarvis parle.",
  action: "Commande exécutée.",
  error: "Une difficulté est survenue.",
};

export default function JarvisApp() {
  const state = useJarvis((s) => s.state);

  return (
    <main className="min-h-dvh bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900 text-cyan-50">
      <div className="mx-auto flex max-w-2xl flex-col items-center gap-6 px-4 py-8">
        <header className="text-center">
          <h1 className="text-2xl font-semibold tracking-wide text-cyan-100">
            J·A·R·V·I·S
          </h1>
          <p className="mt-1 text-xs uppercase tracking-[0.3em] text-cyan-700/70">
            Majordome personnel IA
          </p>
        </header>

        <div className="flex justify-center">
          <AvatarHUD state={state} amplitude={0.2} size={280} />
        </div>

        <div className="text-center text-sm text-cyan-300/80 transition-opacity">
          {STATE_LABELS[state] ?? STATE_LABELS.idle}
        </div>

        <CommandComposer />

        <Transcript />

        <footer className="mt-4 text-center text-[10px] uppercase tracking-widest text-cyan-700/50">
          Backend : Freebox Delta · LLM : Claude Haiku 4.5
        </footer>
      </div>
    </main>
  );
}
