/**
 * Client HTTP minimaliste vers le webhook n8n Jarvis.
 *
 * Envoie le texte transcrit (ou directement saisi) au backend hébergé sur la
 * Freebox Delta de Denis via n8n. Renvoie la réponse structurée
 * { speak, executions, llm_latency_ms, ... }.
 */

import { getBearerToken } from "./auth";
import {
  JARVIS_ADMIN_URL,
  JARVIS_USER_ID,
  JARVIS_WEBHOOK_URL,
  JARVIS_WELCOME_URL,
} from "./config";

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

/**
 * Parse le corps JSON d'une réponse OK sans jamais lever « Unexpected end of
 * JSON input ». Un corps VIDE survient quand le webhook n8n coupe sur dépassement
 * de délai (le backend a mis trop de temps) — on renvoie alors une erreur lisible
 * façon majordome au lieu d'un crash brut (PRD §30.12).
 */
async function parseJsonOrThrow<T>(response: Response): Promise<T> {
  const raw = await response.text();
  if (!raw.trim()) {
    throw new JarvisApiError(
      "Je crains d'avoir mis trop de temps à vous répondre. Auriez-vous l'obligeance de réessayer ?",
      504
    );
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    throw new JarvisApiError("Réponse inattendue de Jarvis.", response.status);
  }
}

export const headers = (): Record<string, string> => {
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
export async function sendTextCommand(
  text: string,
  displayName?: string | null
): Promise<JarvisResponse> {
  if (!text.trim()) {
    throw new Error("Texte vide");
  }

  const body: Record<string, unknown> = {
    text: text.trim(),
    user_id: JARVIS_USER_ID,
  };
  if (displayName && displayName.trim()) {
    body.display_name = displayName.trim();
  }
  const response = await fetch(JARVIS_WEBHOOK_URL, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
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

  return parseJsonOrThrow<JarvisResponse>(response);
}

// ---------------------------------------------------------------------------
// RBAC (PRD §30) — routes relayées par des webhooks n8n dédiés (HTTPS), qui
// transmettent le Bearer de session au backend. On ne parle PAS au backend en
// direct (une page HTTPS ne peut pas joindre le backend servi en HTTP).
// ---------------------------------------------------------------------------

async function failFrom(response: Response): Promise<never> {
  let detail = "";
  try {
    const body = (await response.json()) as { error?: string; detail?: string };
    detail = body.error || body.detail || JSON.stringify(body);
  } catch {
    detail = await response.text();
  }
  throw new JarvisApiError(
    `Jarvis a refusé la requête (${response.status}) : ${detail}`,
    response.status
  );
}

export interface WelcomeResponse {
  speak: string;
  role: "admin" | "locataire" | "visiteur";
  title: string;
  speak_audio_base64?: string | null;
  speak_audio_mime?: string | null;
}

export interface RoleCapabilities {
  converse: boolean;
  safe: boolean;
  sensible: boolean;
  critique: boolean;
}

export interface AdminRolesResponse {
  roles: Record<string, RoleCapabilities>;
  capabilities: string[];
}

/** Discours d'accueil adapté au rôle (joué à la connexion) + rôle faisant autorité. */
export async function getWelcome(displayName?: string | null): Promise<WelcomeResponse> {
  const response = await fetch(JARVIS_WELCOME_URL, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(
      displayName && displayName.trim() ? { display_name: displayName.trim() } : {}
    ),
  });
  if (!response.ok) await failFrom(response);
  return parseJsonOrThrow<WelcomeResponse>(response);
}

/** État des capacités par rôle (écran admin). Réservé admin (403 sinon). */
export async function getAdminRoles(): Promise<AdminRolesResponse> {
  const response = await fetch(JARVIS_ADMIN_URL, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ op: "roles_get" }),
  });
  if (!response.ok) await failFrom(response);
  return parseJsonOrThrow<AdminRolesResponse>(response);
}

/** Accorde/retire un niveau d'action à un rôle (élévation en direct). */
export async function setAdminRole(
  role: string,
  capability: string,
  allowed: boolean
): Promise<{ status: string; roles: AdminRolesResponse["roles"] }> {
  const response = await fetch(JARVIS_ADMIN_URL, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ op: "roles_set", role, capability, allowed }),
  });
  if (!response.ok) await failFrom(response);
  return parseJsonOrThrow<{ status: string; roles: AdminRolesResponse["roles"] }>(
    response
  );
}

/** Ferme toutes les sessions d'un rôle (déconnexion jury). */
export async function disconnectRole(
  role: string
): Promise<{ status: string; role: string; sessions_closed: number }> {
  const response = await fetch(JARVIS_ADMIN_URL, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ op: "disconnect", role }),
  });
  if (!response.ok) await failFrom(response);
  return parseJsonOrThrow<{
    status: string;
    role: string;
    sessions_closed: number;
  }>(response);
}
