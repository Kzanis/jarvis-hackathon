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

/** Temps maximal d'enregistrement micro avant envoi auto (en ms). */
export const MIC_MAX_DURATION_MS = 8_000;

/** Seuil de silence avant arrêt automatique (en ms). */
export const MIC_SILENCE_TIMEOUT_MS = 1_500;
