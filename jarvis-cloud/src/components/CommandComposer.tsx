"use client";

/**
 * CommandComposer — saisie texte + bouton micro + lecture vocale.
 *
 * Cycle UX :
 *   Idle → (tap micro) → Listening → (Web Speech reco) → texte
 *        → Thinking (appel n8n) → Speaking (TTS lit la réponse) → Idle
 *
 * Pattern speak-first : on push immédiatement le user dans le transcript,
 * passe en "thinking", attend la réponse, lit la phrase à voix haute,
 * passe en "action" (flash vert), puis retour "idle".
 */

import { useEffect, useRef, useState } from "react";

import { JarvisApiError, sendTextCommand } from "@/lib/jarvis-api";
import { useJarvis } from "@/lib/store";
import {
  type HandsFreeController,
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  listenOnce,
  playBase64Audio,
  preloadVoices,
  speak,
  startHandsFree,
} from "@/lib/voice";

export function CommandComposer() {
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceReady, setVoiceReady] = useState(false);
  const [handsFreeOn, setHandsFreeOn] = useState(false);
  const [handsFreeStatus, setHandsFreeStatus] = useState<string>("");
  const handsFreeCtrl = useRef<HandsFreeController | null>(null);

  const setState = useJarvis((s) => s.setState);
  const pushUser = useJarvis((s) => s.pushUser);
  const pushJarvis = useJarvis((s) => s.pushJarvis);
  const setResponse = useJarvis((s) => s.setResponse);
  const setError = useJarvis((s) => s.setError);

  useEffect(() => {
    preloadVoices();
    setVoiceReady(true);
  }, []);

  // Cleanup mode mains libres au démontage
  useEffect(() => {
    return () => {
      handsFreeCtrl.current?.stop();
      handsFreeCtrl.current = null;
    };
  }, []);

  const submit = async (overrideText?: string) => {
    const trimmed = (overrideText ?? text).trim();
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
      // Mute le mode mains libres pendant que Jarvis parle (anti-feedback)
      handsFreeCtrl.current?.pause();
      // Priorité 1 : voix Andrew Edge-TTS (mp3 base64 généré côté backend)
      // Priorité 2 : voix système navigateur (Web Speech) en fallback
      // Priorité 3 : simple délai proportionnel à la longueur du texte
      let played = false;
      if (result.speak_audio_base64 && result.speak.trim()) {
        try {
          await playBase64Audio(
            result.speak_audio_base64,
            result.speak_audio_mime ?? "audio/mpeg"
          );
          played = true;
        } catch {
          /* tombe sur Web Speech ci-dessous */
        }
      }
      if (!played && isSpeechSynthesisSupported() && result.speak.trim()) {
        await speak(result.speak);
        played = true;
      }
      if (!played) {
        const wait = Math.min(8_000, 1_500 + result.speak.length * 50);
        await new Promise((r) => setTimeout(r, wait));
      }
      // Reprend l'écoute mains libres une fois que Jarvis a fini de parler
      handsFreeCtrl.current?.resume();
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

  const startListening = async () => {
    if (!isSpeechRecognitionSupported() || pending || listening) return;
    setListening(true);
    setError(null);
    setState("listening");
    try {
      const transcript = await listenOnce({
        onPartial: (p) => setText(p),
      });
      setText("");
      await submit(transcript);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      // Pas une vraie erreur si l'utilisateur n'a rien dit, juste retour à idle
      if (!message.includes("Aucun texte")) {
        setError(message);
      } else {
        setState("idle");
      }
    } finally {
      setListening(false);
    }
  };

  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  const toggleHandsFree = () => {
    if (handsFreeOn) {
      handsFreeCtrl.current?.stop();
      handsFreeCtrl.current = null;
      setHandsFreeOn(false);
      setHandsFreeStatus("");
      if (useJarvis.getState().state === "listening") {
        useJarvis.getState().setState("idle");
      }
      return;
    }
    if (!isSpeechRecognitionSupported()) {
      setError("Mode mains libres indisponible (navigateur non supporté).");
      return;
    }
    const ctrl = startHandsFree({
      onWakeDetected: () => {
        setHandsFreeStatus("Jarvis vous écoute…");
        setState("listening");
      },
      onCommand: (cmd) => {
        setHandsFreeStatus("");
        void submit(cmd);
      },
      onPartial: (live) => {
        setHandsFreeStatus(live.length > 80 ? "…" + live.slice(-80) : live);
      },
      onError: (msg) => {
        setError(msg);
        setHandsFreeOn(false);
        setHandsFreeStatus("");
      },
    });
    if (ctrl) {
      handsFreeCtrl.current = ctrl;
      setHandsFreeOn(true);
      setHandsFreeStatus("En écoute… dites « Jarvis » pour commencer.");
      setState("listening");
    }
  };

  const micSupported = voiceReady && isSpeechRecognitionSupported();

  return (
    <div className="flex flex-col gap-3 w-full max-w-xl">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => void startListening()}
          disabled={pending || listening || !micSupported}
          className={
            "rounded-full p-3 transition " +
            (listening
              ? "bg-cyan-400 animate-pulse text-slate-950"
              : "bg-cyan-500/90 hover:bg-cyan-400 text-slate-950 disabled:bg-cyan-500/30 disabled:text-slate-400 disabled:cursor-not-allowed")
          }
          aria-label={listening ? "Écoute en cours" : "Activer le micro"}
          title={
            !micSupported
              ? "La reconnaissance vocale n'est pas supportée sur ce navigateur"
              : listening
              ? "Écoute en cours…"
              : "Parler à Jarvis"
          }
        >
          {/* Icône micro SVG */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-6 w-6"
          >
            <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" />
            <path d="M19 11a1 1 0 1 0-2 0 5 5 0 0 1-10 0 1 1 0 1 0-2 0 7 7 0 0 0 6 6.93V20H8a1 1 0 1 0 0 2h8a1 1 0 1 0 0-2h-3v-2.07A7 7 0 0 0 19 11Z" />
          </svg>
        </button>

        <input
          className="flex-1 rounded-lg border border-cyan-500/40 bg-slate-900/80 px-4 py-3 text-cyan-50 placeholder:text-cyan-700/70 outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/40"
          placeholder={
            listening
              ? "Parlez maintenant…"
              : 'ex : "Jarvis, ferme le volet de la buanderie"'
          }
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={pending || listening}
        />

        <button
          type="button"
          onClick={() => void submit()}
          disabled={pending || listening || !text.trim()}
          className="rounded-lg bg-cyan-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-500/40"
        >
          {pending ? "..." : "Envoyer"}
        </button>
      </div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-cyan-700/70 flex-1">
          {micSupported
            ? "Appuyez sur le micro, ou tapez. Activez le mode mains libres pour parler à Jarvis sans toucher au téléphone."
            : "Saisie au clavier uniquement (votre navigateur ne supporte pas la dictée vocale)."}
        </p>
        {micSupported && (
          <button
            type="button"
            onClick={toggleHandsFree}
            className={
              "shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold transition " +
              (handsFreeOn
                ? "bg-cyan-400 text-slate-950 shadow-[0_0_20px_rgba(34,211,238,0.5)]"
                : "border border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/10")
            }
            aria-pressed={handsFreeOn}
            title='Mode mains libres : dites "Jarvis [commande]"'
          >
            {handsFreeOn ? "● Mains libres ON" : "Mains libres"}
          </button>
        )}
      </div>
      {handsFreeOn && handsFreeStatus && (
        <p className="text-xs text-cyan-400/80 italic truncate">
          {handsFreeStatus}
        </p>
      )}
    </div>
  );
}
