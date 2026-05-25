/**
 * Client HTTP minimaliste vers le webhook n8n Jarvis.
 *
 * Envoie le texte transcrit (ou directement saisi) au backend hébergé sur la
 * Freebox Delta de Denis via n8n. Renvoie la réponse structurée
 * { speak, executions, llm_latency_ms, ... }.
 */

import { getBearerToken } from "./auth";
import { JARVIS_USER_ID, JARVIS_WEBHOOK_URL } from "./config";

export interface JarvisExecution {
  domain: string;
  tool_name: string;
  correlation_id: string;
  status: string;
  duration_ms: number;
  error: string | null;
  response: Record<string, unknown>;
}

export interface JarvisResponse {
  speak: string;
  executions: JarvisExecution[];
  llm_latency_ms: number;
  llm_provider: string;
  llm_model: string;
  input_tokens: number;
  output_tokens: number;
  stop_reason: string;
  rejection_reason: string | null;
  /** mp3 base64 généré côté backend par Edge-TTS Andrew. */
  speak_audio_base64?: string | null;
  speak_audio_mime?: string | null;
}

export interface JarvisErrorResponse {
  error: string;
  timestamp: string;
}

export class JarvisApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "JarvisApiError";
    this.status = status;
  }
}

const headers = (): Record<string, string> => {
  /*
   * Le token de session est récupéré dynamiquement depuis localStorage
   * (rempli après /login). Plus de Bearer Token statique dans le bundle JS.
   */
  const h: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const sessionToken = getBearerToken();
  if (sessionToken) {
    h["Authorization"] = `Bearer ${sessionToken}`;
  }
  return h;
};

/** Envoie un texte (déjà transcrit) au backend Jarvis via n8n. */
export async function sendTextCommand(text: string): Promise<JarvisResponse> {
  if (!text.trim()) {
    throw new Error("Texte vide");
  }

  const response = await fetch(JARVIS_WEBHOOK_URL, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ text: text.trim(), user_id: JARVIS_USER_ID }),
  });

  if (!response.ok) {
    let detail = "";
    try {
      const errorBody = (await response.json()) as JarvisErrorResponse;
      detail = errorBody.error || JSON.stringify(errorBody);
    } catch {
      detail = await response.text();
    }
    throw new JarvisApiError(
      `Jarvis a refusé la requête (${response.status}) : ${detail}`,
      response.status
    );
  }

  return (await response.json()) as JarvisResponse;
}
