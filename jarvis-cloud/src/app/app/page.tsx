"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AvatarHUD } from "@/components/AvatarHUD";
import { CommandComposer } from "@/components/CommandComposer";
import { Transcript } from "@/components/Transcript";
import { clearSession, getSession } from "@/lib/auth";
import { useJarvis } from "@/lib/store";

const stateLabels = (title: string): Record<string, string> => ({
  idle: `À votre service, ${title}.`,
  listening: "Je vous écoute…",
  thinking: "Permettez-moi un instant…",
  speaking: "Jarvis parle.",
  action: "Commande exécutée.",
  error: "Une difficulté est survenue.",
});

export default function JarvisApp() {
  const router = useRouter();
  const state = useJarvis((s) => s.state);
  const [userId, setUserId] = useState<string | null>(null);
  const [title, setTitle] = useState("Monsieur");
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const session = getSession();
    if (!session) {
      router.replace("/login");
      return;
    }
    setUserId(session.user_id);
    setTitle(session.title || "Monsieur");
    setAuthChecked(true);
  }, [router]);

  const onLogout = () => {
    clearSession();
    useJarvis.getState().reset();
    router.replace("/login");
  };

  if (!authChecked) {
    return (
      <main className="min-h-dvh bg-slate-950 text-cyan-300/70 flex items-center justify-center">
        <p className="text-sm">Vérification de l&apos;accès…</p>
      </main>
    );
  }

  return (
    <main className="min-h-dvh bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900 text-cyan-50">
      <div className="mx-auto flex max-w-2xl flex-col items-center gap-6 px-4 py-8">
        <header className="flex w-full items-start justify-between">
          <div className="text-center mx-auto">
            <h1 className="text-2xl font-semibold tracking-wide text-cyan-100">
              J·A·R·V·I·S
            </h1>
            <p className="mt-1 text-xs uppercase tracking-[0.3em] text-cyan-700/70">
              Majordome personnel IA
            </p>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="ml-2 shrink-0 rounded-full border border-cyan-500/30 px-3 py-1 text-[10px] uppercase tracking-widest text-cyan-300/80 hover:bg-cyan-500/10"
            title={userId ? `Déconnexion de ${userId}` : "Se déconnecter"}
          >
            Déconnexion
          </button>
        </header>

        <div className="flex justify-center">
          <AvatarHUD state={state} amplitude={0.2} size={280} />
        </div>

        <div className="text-center text-sm text-cyan-300/80 transition-opacity">
          {stateLabels(title)[state] ?? stateLabels(title).idle}
        </div>

        <CommandComposer title={title} />

        <Transcript />

        <footer className="mt-4 text-center text-[10px] uppercase tracking-widest text-cyan-700/50">
          Backend : Freebox Delta · LLM : Claude Haiku 4.5
        </footer>
      </div>
    </main>
  );
}
