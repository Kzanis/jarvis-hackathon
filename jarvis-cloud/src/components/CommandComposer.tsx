"use client";

/**
 * CommandComposer — saisie texte (mode démarrage) + bouton "envoi".
 *
 * V1 : envoie un texte au backend Jarvis via le webhook n8n.
 * V1.1 (à venir) : bouton micro réel avec MediaRecorder → POST /intent/audio.
 *
 * Pattern speak-first : on push immédiatement le user dans le transcript,
 * passe en état "thinking", attend la réponse, puis affiche la phrase
 * majordome et passe en "speaking" pendant que le TTS jouerait (à brancher).
 */

import { useState } from "react";

import { JarvisApiError, sendTextCommand } from "@/lib/jarvis-api";
import { useJarvis } from "@/lib/store";

export function CommandComposer() {
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);

  const setState = useJarvis((s) => s.setState);
  const pushUser = useJarvis((s) => s.pushUser);
  const pushJarvis = useJarvis((s) => s.pushJarvis);
  const setResponse = useJarvis((s) => s.setResponse);
  const setError = useJarvis((s) => s.setError);

  const submit = async () => {
    const trimmed = text.trim();
    if (!trimmed || pending) return;

    setPending(true);
    setError(null);
    setText("");
    pushUser(trimmed);
    setState("thinking");

    try {
      const result = await sendTextCommand(trimmed);
      setResponse(result);
      pushJarvis(result.speak);
      setState("speaking");
      // Auto-retour à idle après un délai proportionnel à la phrase
      const wait = Math.min(8_000, 1_500 + result.speak.length * 50);
      setTimeout(() => {
        if (useJarvis.getState().state === "speaking") {
          useJarvis.getState().setState(
            result.executions.length > 0 ? "action" : "idle"
          );
          setTimeout(() => {
            if (useJarvis.getState().state === "action") {
              useJarvis.getState().setState("idle");
            }
          }, 1_200);
        }
      }, wait);
    } catch (err) {
      const message =
        err instanceof JarvisApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : "Erreur inconnue";
      setError(message);
    } finally {
      setPending(false);
    }
  };

  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  return (
    <div className="flex flex-col gap-3 w-full max-w-xl">
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-lg border border-cyan-500/40 bg-slate-900/80 px-4 py-3 text-cyan-50 placeholder:text-cyan-700/70 outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/40"
          placeholder='ex : "Jarvis, ferme le volet de la buanderie"'
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={pending}
        />
        <button
          type="button"
          onClick={() => void submit()}
          disabled={pending || !text.trim()}
          className="rounded-lg bg-cyan-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-500/40"
        >
          {pending ? "..." : "Envoyer"}
        </button>
      </div>
      <p className="text-xs text-cyan-700/70">
        V1 texte uniquement. Le bouton micro arrive dès que la PWA est
        déployée sur Hostinger (HTTPS requis pour MediaRecorder).
      </p>
    </div>
  );
}
