"use client";

import { useEffect, useState } from "react";

import {
  AdminRolesResponse,
  disconnectRole,
  getAdminRoles,
  JarvisApiError,
  setAdminRole,
} from "@/lib/jarvis-api";

// Libellés en français clair (le backend renvoie les clés techniques).
const ROLE_LABELS: Record<string, string> = {
  admin: "Administrateur",
  locataire: "Locataire",
  visiteur: "Visiteur / Jury",
};

const CAP_LABELS: Record<string, string> = {
  safe: "Actions simples",
  sensible: "Portail · garage",
  critique: "Alarme",
};

function errorMessage(e: unknown): string {
  if (e instanceof JarvisApiError) {
    if (e.status === 403) return "Réservé à l'administrateur (ou session expirée).";
    if (e.status === 0) return "Backend direct non configuré (NEXT_PUBLIC_JARVIS_API_URL).";
    return e.message;
  }
  return e instanceof Error ? e.message : "Erreur inconnue.";
}

/**
 * Panneau d'administration des accès par rôle (RBAC, PRD §30).
 * Visible UNIQUEMENT pour l'admin (gating cosmétique : la vraie sécurité est le
 * 403 backend sur le Bearer). Permet l'élévation en direct et la déconnexion jury.
 */
export function AdminPanel() {
  const [roles, setRoles] = useState<AdminRolesResponse["roles"] | null>(null);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getAdminRoles()
      .then((r) => {
        setRoles(r.roles);
        setCapabilities(r.capabilities);
      })
      .catch((e) => setError(errorMessage(e)));
  }, []);

  const toggle = async (role: string, capability: string, allowed: boolean) => {
    if (busy) return;
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const res = await setAdminRole(role, capability, allowed);
      setRoles(res.roles);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const onDisconnect = async (role: string) => {
    if (busy) return;
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const res = await disconnectRole(role);
      setInfo(
        `${res.sessions_closed} session(s) « ${ROLE_LABELS[role] ?? role} » fermée(s).`
      );
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="w-full rounded-lg border border-cyan-500/20 bg-slate-900/40 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs uppercase tracking-[0.3em] text-cyan-300/80">
          Accès par rôle
        </h2>
        {busy && <span className="text-[10px] text-cyan-700/70">…</span>}
      </div>

      {error && (
        <div className="mb-3 rounded-lg border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-sm text-orange-200">
          {error}
        </div>
      )}
      {info && (
        <div className="mb-3 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-100">
          {info}
        </div>
      )}

      {!roles && !error && (
        <p className="text-sm text-cyan-700/70">Chargement des rôles…</p>
      )}

      {roles && (
        <div className="flex flex-col gap-3">
          {Object.keys(roles).map((role) => {
            const caps = roles[role];
            const isAdmin = role === "admin";
            return (
              <div
                key={role}
                className="rounded-lg border border-cyan-500/10 bg-slate-950/40 p-3"
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-semibold text-cyan-100">
                    {ROLE_LABELS[role] ?? role}
                  </span>
                  {!isAdmin && (
                    <button
                      type="button"
                      onClick={() => onDisconnect(role)}
                      disabled={busy}
                      className="rounded-full border border-orange-500/40 px-2.5 py-1 text-[10px] uppercase tracking-widest text-orange-200/90 transition hover:bg-orange-500/10 disabled:opacity-40"
                    >
                      Déconnexion
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {capabilities.map((cap) => {
                    const on = !!caps[cap as keyof typeof caps];
                    const locked = isAdmin || busy;
                    return (
                      <button
                        key={cap}
                        type="button"
                        disabled={locked}
                        onClick={() => toggle(role, cap, !on)}
                        title={
                          isAdmin
                            ? "Le rôle administrateur n'est pas modifiable"
                            : undefined
                        }
                        className={[
                          "rounded-full border px-3 py-1 text-[11px] tracking-wide transition",
                          on
                            ? "border-cyan-400/60 bg-cyan-500/20 text-cyan-100"
                            : "border-slate-600/40 bg-slate-800/40 text-cyan-700/70",
                          locked
                            ? "cursor-not-allowed opacity-50"
                            : "hover:border-cyan-400",
                        ].join(" ")}
                      >
                        {CAP_LABELS[cap] ?? cap} · {on ? "ON" : "OFF"}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p className="mt-3 text-[10px] uppercase tracking-widest text-cyan-700/50">
        Accordez un accès le temps d&apos;une démonstration — ou coupez les sessions visiteur d&apos;un geste.
      </p>
    </section>
  );
}
