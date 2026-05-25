/**
 * Gestion de la session utilisateur Jarvis (localStorage, côté navigateur).
 *
 * Le token Bearer n'est PLUS dans le bundle JS public — il est récupéré
 * via /login après authentification. Stocké en localStorage avec son expiry.
 * Si expiré ou absent, l'utilisateur est redirigé vers /login.
 */

const STORAGE_KEY = "jarvis_session_v1";

const LOGIN_URL =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_JARVIS_LOGIN_URL) ||
  "https://creatorweb.fr/webhook/jarvis-login";

export interface JarvisSession {
  token: string;
  user_id: string;
  expires_at: string; // ISO 8601 (UTC)
}

export function getSession(): JarvisSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as JarvisSession;
    if (!parsed.token || !parsed.expires_at) return null;
    if (new Date(parsed.expires_at).getTime() < Date.now()) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function setSession(session: JarvisSession): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function getBearerToken(): string | null {
  const session = getSession();
  return session ? session.token : null;
}

export class LoginError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "LoginError";
    this.status = status;
  }
}

/** Tente le login contre n8n. Stocke la session en cas de succès. */
export async function loginRequest(
  username: string,
  password: string
): Promise<JarvisSession> {
  if (!username.trim() || !password) {
    throw new LoginError("Identifiant et mot de passe requis", 400);
  }
  const response = await fetch(LOGIN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: username.trim(), password }),
  });
  if (!response.ok) {
    let detail = "";
    try {
      const body = (await response.json()) as { error?: string; detail?: string };
      detail = body.error || body.detail || "";
    } catch {
      detail = await response.text();
    }
    throw new LoginError(
      detail || `Échec de connexion (HTTP ${response.status})`,
      response.status
    );
  }
  const data = (await response.json()) as JarvisSession;
  if (!data.token || !data.expires_at) {
    throw new LoginError("Réponse de connexion invalide", 502);
  }
  setSession(data);
  return data;
}

export async function logoutRequest(): Promise<void> {
  clearSession();
}
