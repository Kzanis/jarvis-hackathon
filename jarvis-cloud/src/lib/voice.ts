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
  // Préférence : voix MASCULINES fr-FR uniquement (Thomas iOS, Paul/Daniel/Henri),
  // puis Google français en dernier recours. On ne met PAS de voix féminine ici :
  // sinon le repli navigateur (sur mobile surtout) sort une voix de femme.
  const preferred = ["thomas", "paul", "daniel", "henri", "google français"];
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
    if (!isSpeechSynthesisSupported() || !text || !text.trim()) {
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
  // État "armé" : true après détection du mot-clé, en attente de la commande.
  // Nécessaire car en dictée continue le wake word et la commande arrivent
  // souvent dans deux résultats finaux séparés.
  let armed = false;
  let armTimer: ReturnType<typeof setTimeout> | null = null;
  const ARM_TIMEOUT_MS = 12_000;

  const clearRestart = () => {
    if (restartTimer !== null) {
      clearTimeout(restartTimer);
      restartTimer = null;
    }
  };

  const disarm = () => {
    armed = false;
    if (armTimer !== null) {
      clearTimeout(armTimer);
      armTimer = null;
    }
  };

  const arm = () => {
    armed = true;
    if (armTimer !== null) clearTimeout(armTimer);
    armTimer = setTimeout(() => { armed = false; armTimer = null; }, ARM_TIMEOUT_MS);
    options.onWakeDetected?.();
  };

  const dispatch = (command: string) => {
    const now = Date.now();
    if (now - lastCommandTs < 2000) return; // anti-doublon (iOS répète parfois)
    lastCommandTs = now;
    disarm();
    options.onCommand(command);
  };

  const cleanCommand = (s: string) =>
    s.trim().replace(/^[,;.!?:]+/, "").trim();

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

    // On ne déclenche que sur résultat final (les interims servent à l'affichage).
    if (!final) return;

    const match = final.match(WAKE_REGEX);

    if (match) {
      // Le segment final contient le mot-clé : la commande est ce qui suit.
      const afterIdx =
        final.toLowerCase().indexOf(match[0].toLowerCase()) + match[0].length;
      const command = cleanCommand(final.slice(afterIdx));
      if (command.length >= 2) {
        dispatch(command); // "OK Jarvis, ferme le garage" en une fois
      } else {
        arm(); // "OK Jarvis" seul → on attend la commande à l'énoncé suivant
      }
      return;
    }

    // Pas de mot-clé dans ce segment : s'il fait suite à un réveil, c'est la commande.
    if (armed) {
      const command = cleanCommand(final);
      if (command.length >= 2) dispatch(command);
    }
  };

  const start = () => {
    if (!active) return;
    try {
      recognition = buildRecognition();
      recognition.onresult = handleResult;
      recognition.onerror = (e) => {
        // Erreurs benignes à ignorer : "aborted" est provoqué par NOUS quand on
        // appelle abort() (pause pendant le TTS, ou stop). "no-speech"/"audio-capture"
        // = silence prolongé. Dans tous ces cas on laisse onend relancer l'écoute.
        if (
          e.error === "no-speech" ||
          e.error === "audio-capture" ||
          e.error === "aborted"
        ) {
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
      disarm();
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

// ---------------------------------------------------------------------------
// Lecture audio mobile-safe.
// Sur mobile, l'autoplay est interdit hors d'un geste utilisateur. On utilise
// donc UN SEUL élément <audio>, "débloqué" au moment d'un tap (bouton mains
// libres). Une fois cet élément amorcé, la lecture programmatique ultérieure
// (accusé Andrew + réponses du backend) est autorisée, y compris quand elle est
// déclenchée par la détection vocale et non par un appui.
// ---------------------------------------------------------------------------
let sharedAudio: HTMLAudioElement | null = null;

function getSharedAudio(): HTMLAudioElement {
  if (!sharedAudio) sharedAudio = new Audio();
  return sharedAudio;
}

/**
 * À appeler DANS un geste utilisateur (tap sur « mains libres »/micro) pour
 * débloquer l'autoplay sur mobile. Joue brièvement l'accusé en muet puis le
 * remet à zéro — l'élément partagé est dès lors autorisé à rejouer seul.
 */
export function unlockAudio(): void {
  if (typeof window === "undefined") return;
  try {
    const a = getSharedAudio();
    a.src = "/oui-monsieur.mp3";
    a.muted = true;
    const p = a.play();
    if (p && typeof p.then === "function") {
      p.then(() => {
        a.pause();
        a.currentTime = 0;
        a.muted = false;
      }).catch(() => {
        a.muted = false;
      });
    }
  } catch {
    /* ignore */
  }
}

/** Joue une source audio sur l'élément partagé (débloqué). */
function playOnShared(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const a = getSharedAudio();
    a.muted = false;
    a.onended = () => resolve();
    a.onerror = () => reject(new Error("Lecture audio échouée."));
    a.src = src;
    const p = a.play();
    if (p && typeof p.then === "function") p.catch((e) => reject(e));
  });
}

/**
 * Joue un mp3 fourni en base64 (généré par Edge-TTS Andrew côté backend).
 * Passe par l'élément partagé débloqué pour fonctionner sur mobile.
 * Résout à la fin, rejette en cas d'échec (le repli Web Speech est géré en amont).
 */
export function playBase64Audio(
  base64: string,
  mime: string = "audio/mpeg"
): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  return playOnShared(`data:${mime};base64,${base64}`);
}

/**
 * Joue l'accusé de réveil « Oui, Monsieur. » en voix Andrew (MP3 statique servi
 * par le front, identique sur tous les appareils). Repli sur la synthèse
 * navigateur si le MP3 ne peut pas être joué. Résout toujours.
 */
export function playWakeAck(title: string = "Monsieur"): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  // Accusé genré selon l'utilisateur connecté (Andrew reste la voix de Jarvis).
  const isMadame = title.toLowerCase().startsWith("madame");
  const src = isMadame ? "/oui-madame.mp3" : "/oui-monsieur.mp3";
  const fallback = isMadame ? "Oui, Madame." : "Oui, Monsieur.";
  // Élément partagé débloqué → joue sur mobile. Repli voix navigateur si échec.
  return playOnShared(src).catch(() => speak(fallback));
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
