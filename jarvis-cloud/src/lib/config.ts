/**
 * Configuration centrale du frontend Jarvis.
 *
 * IMPORTANT : utilisation d'accès STATIQUES à process.env.NEXT_PUBLIC_*
 * (pas d'indirection via variable) — Next.js doit pouvoir inliner les
 * valeurs au build time. Un helper avec `process.env[key]` dynamique
 * ne fonctionne PAS en mode `output: 'export'`.
 */

/** URL du webhook n8n qui relaie vers la Freebox VM Jarvis. */
export const JARVIS_WEBHOOK_URL =
  process.env.NEXT_PUBLIC_JARVIS_WEBHOOK_URL ||
  "https://creatorweb.fr/webhook/jarvis-command";

/** Identifiant de l'utilisateur courant (Denis par défaut). */
export const JARVIS_USER_ID =
  process.env.NEXT_PUBLIC_JARVIS_USER_ID || "denis";

/**
 * Webhook n8n de l'accueil parlé (RBAC, PRD §30) : relaie vers le backend
 * /auth/welcome en transmettant le Bearer. Même principe que login/command :
 * un webhook HTTPS par opération (le front ne parle jamais au backend en direct).
 */
export const JARVIS_WELCOME_URL =
  process.env.NEXT_PUBLIC_JARVIS_WELCOME_URL ||
  "https://creatorweb.fr/webhook/jarvis-welcome";

/**
 * Webhook n8n de l'administration des rôles : relaie vers le backend
 * /admin/roles (lecture/écriture) et /admin/disconnect-role selon le champ `op`.
 */
export const JARVIS_ADMIN_URL =
  process.env.NEXT_PUBLIC_JARVIS_ADMIN_URL ||
  "https://creatorweb.fr/webhook/jarvis-admin";

/** Temps maximal d'enregistrement micro avant envoi auto (en ms). */
export const MIC_MAX_DURATION_MS = 8_000;

/** Seuil de silence avant arrêt automatique (en ms). */
export const MIC_SILENCE_TIMEOUT_MS = 1_500;
