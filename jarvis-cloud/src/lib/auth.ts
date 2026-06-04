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

export type JarvisRole = "admin" | "locataire" | "visiteur";

export interface JarvisSession {
  token: string;
  user_id: string;
  title?: string; // "Monsieur" | "Madame" — titre d'adresse renvoyé par le login
  role?: JarvisRole; // rôle RBAC ; complété et fait autorité par GET /auth/welcome
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

/** Rôle RBAC courant. Défaut « visiteur » (le plus restrictif) si absent. */
export function getRole(): JarvisRole {
  const session = getSession();
  return session?.role ?? "visiteur";
}

/** Met à jour le rôle dans la session stockée (rôle faisant autorité renvoyé par /auth/welcome). */
export function updateSessionRole(role: JarvisRole): void {
  const session = getSession();
  if (!session) return;
  setSession({ ...session, role });
}

// ---------------------------------------------------------------------------
// Nom d'adresse choisi par l'utilisateur (« comment dois-je vous appeler ? »).
// Mémorisé par appareil ET par utilisateur, persistant entre les sessions, pour
// n'être demandé qu'une seule fois (PRD §30.4).
// ---------------------------------------------------------------------------

const NAME_KEY = "jarvis_display_name_v1";

export function getDisplayName(userId: string): string | null {
  if (typeof window === "undefined" || !userId) return null;
  try {
    const map = JSON.parse(window.localStorage.getItem(NAME_KEY) || "{}") as Record<string, string>;
    const name = map[userId];
    return name && name.trim() ? name : null;
  } catch {
    return null;
  }
}

export function setDisplayName(userId: string, name: string): void {
  if (typeof window === "undefined" || !userId || !name.trim()) return;
  let map: Record<string, string> = {};
  try {
    map = JSON.parse(window.localStorage.getItem(NAME_KEY) || "{}") as Record<string, string>;
  } catch {
    map = {};
  }
  map[userId] = name.trim();
  window.localStorage.setItem(NAME_KEY, JSON.stringify(map));
}

export function clearDisplayName(userId: string): void {
  if (typeof window === "undefined" || !userId) return;
  try {
    const map = JSON.parse(window.localStorage.getItem(NAME_KEY) || "{}") as Record<string, string>;
    delete map[userId];
    window.localStorage.setItem(NAME_KEY, JSON.stringify(map));
  } catch {
    /* ignore */
  }
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
