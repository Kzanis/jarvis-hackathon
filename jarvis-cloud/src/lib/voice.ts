"use client";

/**
 * Voice — helpers pour la PWA Jarvis.
 *
 * STT : Web Speech API (SpeechRecognition) fr-FR, navigateur natif.
 * TTS : Web Speech API (SpeechSynthesis) avec voix masculine fr-FR si dispo.
 *
 * Plus tard (V2) : bascule sur backend Edge-TTS Andrew + Whisper via POST /intent/audio_full.
 */

type SR = typeof window extends { SpeechRecognition: infer R } ? R : unknown;

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: { results: ArrayLike<{ 0: { transcript: string } }>; resultIndex: number }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

const getRecognitionCtor = (): (new () => SpeechRecognitionLike) | null => {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
};

export const isSpeechRecognitionSupported = (): boolean =>
  getRecognitionCtor() !== null;

/**
 * Lance une reconnaissance vocale unique et résout avec la transcription.
 * onPartial : callback optionnel pour afficher les transcriptions partielles.
 */
export function listenOnce(options?: {
  language?: string;
  onPartial?: (partial: string) => void;
  onStart?: () => void;
}): Promise<string> {
  return new Promise((resolve, reject) => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) {
      reject(new Error("La reconnaissance vocale n'est pas supportée sur ce navigateur."));
      return;
    }
    const recognition = new Ctor();
    recognition.lang = options?.language ?? "fr-FR";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    let finalTranscript = "";

    recognition.onstart = () => options?.onStart?.();
    recognition.onresult = (event) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i] as unknown as {
          0: { transcript: string };
          isFinal?: boolean;
        };
        const transcript = result[0].transcript;
        if (result.isFinal) final += transcript;
        else interim += transcript;
      }
      if (final) finalTranscript += final;
      options?.onPartial?.(finalTranscript + interim);
    };

    recognition.onerror = (event) => reject(new Error(`Reco vocale: ${event.error}`));

    recognition.onend = () => {
      if (finalTranscript.trim()) resolve(finalTranscript.trim());
      else reject(new Error("Aucun texte reconnu."));
    };

    try {
      recognition.start();
    } catch (e) {
      reject(e instanceof Error ? e : new Error(String(e)));
    }
  });
}

// ---------------------------------------------------------------------------
// TTS — SpeechSynthesis
// ---------------------------------------------------------------------------

let cachedVoice: SpeechSynthesisVoice | null = null;

function pickBestFrenchVoice(): SpeechSynthesisVoice | null {
  if (typeof window === "undefined") return null;
  if (cachedVoice) return cachedVoice;
  const all = window.speechSynthesis.getVoices();
  if (!all.length) return null;

  const fr = all.filter((v) => v.lang.toLowerCase().startsWith("fr"));
  // Préférence : Thomas (iOS), Paul, Daniel (masculin), puis Google français, puis n'importe quelle fr.
  const preferred = ["thomas", "paul", "daniel", "henri", "google français", "amélie"];
  for (const name of preferred) {
    const match = fr.find((v) => v.name.toLowerCase().includes(name));
    if (match) {
      cachedVoice = match;
      return match;
    }
  }
  cachedVoice = fr[0] ?? all[0];
  return cachedVoice;
}

export const isSpeechSynthesisSupported = (): boolean =>
  typeof window !== "undefined" && "speechSynthesis" in window;

/** Synthétise et joue une phrase. Retourne quand la lecture est terminée. */
export function speak(
  text: string,
  options?: { rate?: number; pitch?: number; volume?: number }
): Promise<void> {
  return new Promise((resolve) => {
    if (!isSpeechSynthesisSupported() || !text.trim()) {
      resolve();
      return;
    }
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "fr-FR";
    utter.rate = options?.rate ?? 0.95;
    utter.pitch = options?.pitch ?? 0.9; // un peu grave : majordome
    utter.volume = options?.volume ?? 1.0;
    const voice = pickBestFrenchVoice();
    if (voice) utter.voice = voice;

    utter.onend = () => resolve();
    utter.onerror = () => resolve();

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  });
}

/**
 * Mode mains libres : écoute permanente + détection du mot "Jarvis".
 *
 * Quand l'utilisateur prononce "Jarvis [commande]", la commande est extraite
 * et envoyée. Auto-restart si la reconnaissance se coupe (iOS Safari).
 * À appeler `pause()` quand Jarvis parle (TTS) pour éviter le feedback acoustique.
 */

export interface HandsFreeController {
  isActive(): boolean;
  pause(): void;     // pendant TTS playback
  resume(): void;    // après TTS playback
  stop(): void;      // arrêt définitif
}

const WAKE_REGEX = /\b(jarvis|jervis|jarvise|jarviss|jharvis)\b/i;

export function startHandsFree(options: {
  onWakeDetected?: () => void;
  onCommand: (command: string) => void;
  onPartial?: (text: string) => void;
  onError?: (msg: string) => void;
  language?: string;
}): HandsFreeController | null {
  const Ctor = getRecognitionCtor();
  if (!Ctor) {
    options.onError?.("La reconnaissance vocale n'est pas supportée sur ce navigateur.");
    return null;
  }

  let recognition: SpeechRecognitionLike | null = null;
  let active = true;
  let paused = false;
  let lastCommandTs = 0;
  let restartTimer: ReturnType<typeof setTimeout> | null = null;

  const clearRestart = () => {
    if (restartTimer !== null) {
      clearTimeout(restartTimer);
      restartTimer = null;
    }
  };

  const buildRecognition = (): SpeechRecognitionLike => {
    const r = new Ctor();
    r.lang = options.language ?? "fr-FR";
    r.continuous = true;
    r.interimResults = true;
    r.maxAlternatives = 1;
    return r;
  };

  const handleResult = (event: { results: ArrayLike<{ 0: { transcript: string } }>; resultIndex: number }) => {
    if (paused) return;
    let interim = "";
    let final = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i] as unknown as {
        0: { transcript: string };
        isFinal?: boolean;
      };
      const t = result[0].transcript;
      if (result.isFinal) final += t;
      else interim += t;
    }
    const live = (final + " " + interim).trim();
    if (live) options.onPartial?.(live);

    // Détecte "jarvis [commande]" dans final (déclenche uniquement sur résultat final)
    if (!final) return;
    const match = final.match(WAKE_REGEX);
    if (!match) return;

    // Tout ce qui suit le wake word = commande
    const afterIdx = final.toLowerCase().indexOf(match[0].toLowerCase()) + match[0].length;
    const command = final.slice(afterIdx).trim().replace(/^[,;.!?:]+/, "").trim();

    if (!command || command.length < 2) {
      // Wake détecté seul → notifier mais ne pas envoyer
      options.onWakeDetected?.();
      return;
    }

    // Anti-doublon (iOS répète parfois la même final)
    const now = Date.now();
    if (now - lastCommandTs < 2000) return;
    lastCommandTs = now;

    options.onCommand(command);
  };

  const start = () => {
    if (!active) return;
    try {
      recognition = buildRecognition();
      recognition.onresult = handleResult;
      recognition.onerror = (e) => {
        if (e.error === "no-speech" || e.error === "audio-capture") {
          // silence prolongé, on relancera via onend
          return;
        }
        options.onError?.(`Reco mains libres : ${e.error}`);
      };
      recognition.onend = () => {
        // Auto-restart tant que le mode est actif et pas en pause
        clearRestart();
        if (active && !paused) {
          restartTimer = setTimeout(start, 300);
        }
      };
      recognition.start();
    } catch (e) {
      options.onError?.(e instanceof Error ? e.message : String(e));
    }
  };

  start();

  return {
    isActive: () => active && !paused,
    pause: () => {
      paused = true;
      clearRestart();
      try { recognition?.abort(); } catch { /* ignore */ }
    },
    resume: () => {
      paused = false;
      start();
    },
    stop: () => {
      active = false;
      clearRestart();
      try {
        if (recognition) {
          // Neutralise les callbacks avant abort : sur iOS, abort() peut
          // déclencher un dernier onend/onerror qui relancerait la boucle.
          recognition.onend = null;
          recognition.onerror = null;
          recognition.onresult = null;
          recognition.abort();
        }
      } catch { /* ignore */ }
      recognition = null;
    },
  };
}

/**
 * Joue un mp3 fourni en base64 (généré par Edge-TTS Andrew côté backend).
 * Résout quand la lecture est terminée.
 */
export function playBase64Audio(
  base64: string,
  mime: string = "audio/mpeg"
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      resolve();
      return;
    }
    try {
      const audio = new Audio(`data:${mime};base64,${base64}`);
      audio.onended = () => resolve();
      audio.onerror = () => reject(new Error("Lecture mp3 base64 échouée."));
      // L'autoplay nécessite un contexte d'interaction utilisateur (tap envoi/micro).
      const playPromise = audio.play();
      if (playPromise && typeof playPromise.then === "function") {
        playPromise.catch((e) => reject(e));
      }
    } catch (e) {
      reject(e instanceof Error ? e : new Error(String(e)));
    }
  });
}

/** Précharge les voix (utile pour iOS où getVoices() est async). */
export function preloadVoices(): void {
  if (!isSpeechSynthesisSupported()) return;
  // Premier appel ; les voix se chargent ensuite
  window.speechSynthesis.getVoices();
  // Déclenchement onvoiceschanged si nécessaire
  if (typeof window.speechSynthesis.addEventListener === "function") {
    const handler = () => {
      cachedVoice = null;
      pickBestFrenchVoice();
      window.speechSynthesis.removeEventListener("voiceschanged", handler);
    };
    window.speechSynthesis.addEventListener("voiceschanged", handler);
  }
}
