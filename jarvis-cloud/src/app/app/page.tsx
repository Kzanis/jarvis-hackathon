"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AdminPanel } from "@/components/AdminPanel";
import { AvatarHUD } from "@/components/AvatarHUD";
import { CommandComposer } from "@/components/CommandComposer";
import { Transcript } from "@/components/Transcript";
import {
  clearSession,
  getSession,
  updateSessionRole,
  type JarvisRole,
} from "@/lib/auth";
import { getWelcome, type WelcomeResponse } from "@/lib/jarvis-api";
import { useJarvis } from "@/lib/store";
import { playBase64Audio } from "@/lib/voice";

// Drapeau (par onglet) pour ne jouer l'accueil qu'une fois par connexion —
// survit au double-montage StrictMode, effacé au logout pour rejouer ensuite.
const WELCOME_FLAG = "jarvis_welcome_played";

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
  const [role, setRole] = useState<JarvisRole>("visiteur");
  const [showAdmin, setShowAdmin] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  // Accueil : si l'autoplay du navigateur refuse de jouer le son (geste trop ancien),
  // on garde le MP3 pour le rejouer via un bouton (clic = geste frais = son garanti).
  const [welcomeAudio, setWelcomeAudio] = useState<WelcomeResponse | null>(null);

  useEffect(() => {
    const session = getSession();
    if (!session) {
      router.replace("/login");
      return;
    }
    setUserId(session.user_id);
    setRole(session.role ?? "visiteur");
    setTitle(session.title || "Monsieur");
    setAuthChecked(true);

    // Accueil parlé, rejoué à CHAQUE connexion (drapeau lié au token de session).
    const alreadyPlayed =
      window.sessionStorage.getItem(WELCOME_FLAG) === session.token;
    if (typeof window !== "undefined" && !alreadyPlayed) {
      window.sessionStorage.setItem(WELCOME_FLAG, session.token);
      getWelcome(null)
        .then((w) => {
          if (w.role) {
            setRole(w.role);
            updateSessionRole(w.role);
          }
          const store = useJarvis.getState();
          store.setState("speaking");
          store.pushJarvis(w.speak);
          setWelcomeAudio(w);
          if (w.speak_audio_base64) {
            // On tente l'autoplay ; qu'il réussisse ou non, le bouton « Écouter »
            // reste affiché (voir rendu) pour (re)lancer la voix d'un clic.
            playBase64Audio(w.speak_audio_base64, w.speak_audio_mime ?? "audio/mpeg")
              .catch(() => {})
              .finally(() => store.setState("idle"));
          } else {
            store.setState("idle");
          }
        })
        .catch(() => {
          // Échec de l'accueil : drapeau retiré pour qu'il soit rejouable.
          window.sessionStorage.removeItem(WELCOME_FLAG);
        });
    }
  }, [router]);

  const replayWelcome = () => {
    if (!welcomeAudio?.speak_audio_base64) return;
    playBase64Audio(
      welcomeAudio.speak_audio_base64,
      welcomeAudio.speak_audio_mime ?? "audio/mpeg"
    ).catch(() => {});
  };

  const onLogout = () => {
    clearSession();
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(WELCOME_FLAG);
    }
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
          <div className="ml-2 flex shrink-0 items-center gap-2">
            {role === "admin" && (
              <button
                type="button"
                onClick={() => setShowAdmin((s) => !s)}
                className={[
                  "rounded-full border px-3 py-1 text-[10px] uppercase tracking-widest transition",
                  showAdmin
                    ? "border-cyan-400/60 bg-cyan-500/20 text-cyan-100"
                    : "border-cyan-500/30 text-cyan-300/80 hover:bg-cyan-500/10",
                ].join(" ")}
                title="Gestion des accès par rôle"
              >
                Admin
              </button>
            )}
            <button
              type="button"
              onClick={onLogout}
              className="rounded-full border border-cyan-500/30 px-3 py-1 text-[10px] uppercase tracking-widest text-cyan-300/80 hover:bg-cyan-500/10"
              title={userId ? `Déconnexion de ${userId}` : "Se déconnecter"}
            >
              Déconnexion
            </button>
          </div>
        </header>

        {role === "admin" && showAdmin && <AdminPanel />}

        <div className="flex justify-center">
          <AvatarHUD state={state} amplitude={0.2} size={280} />
        </div>

        <div className="text-center text-sm text-cyan-300/80 transition-opacity">
          {stateLabels(title)[state] ?? stateLabels(title).idle}
        </div>

        {welcomeAudio?.speak_audio_base64 && (
          <button
            type="button"
            onClick={replayWelcome}
            className="w-full max-w-xl rounded-xl border border-cyan-400/50 bg-cyan-500/15 px-5 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-500/25"
          >
            🔊 Écouter la présentation de Jarvis
          </button>
        )}

        <CommandComposer title={title} />

        <Transcript />

        <footer className="mt-4 text-center text-[10px] uppercase tracking-widest text-cyan-700/50">
          Backend : Freebox Delta · LLM : Claude Haiku 4.5
        </footer>
      </div>
    </main>
  );
}
