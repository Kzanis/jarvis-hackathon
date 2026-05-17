"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getSession, loginRequest, LoginError } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("denis");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    // Si déjà connecté, on bascule directement sur /app
    if (getSession()) {
      router.replace("/app");
    }
  }, [router]);

  const submit: React.FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault();
    if (pending) return;
    setError("");
    setPending(true);
    try {
      await loginRequest(username, password);
      router.replace("/app");
    } catch (err) {
      const message =
        err instanceof LoginError
          ? err.message
          : err instanceof Error
          ? err.message
          : "Erreur inconnue";
      setError(message);
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="min-h-dvh bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900 text-cyan-50">
      <section className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center px-6">
        <header className="mb-10 text-center">
          <p className="mb-2 text-xs uppercase tracking-[0.4em] text-cyan-400/80">
            Accès privé
          </p>
          <h1 className="text-4xl font-semibold tracking-wide text-cyan-100">
            J·A·R·V·I·S
          </h1>
          <p className="mt-1 text-xs uppercase tracking-[0.3em] text-cyan-700/70">
            Identifiez-vous pour continuer
          </p>
        </header>

        <form
          onSubmit={submit}
          className="flex w-full flex-col gap-4 rounded-2xl border border-cyan-500/20 bg-slate-900/60 p-6 backdrop-blur-md"
        >
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-cyan-300/80">Identifiant</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              disabled={pending}
              className="rounded-lg border border-cyan-500/30 bg-slate-950/80 px-3 py-2.5 text-cyan-50 outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/40"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-cyan-300/80">Mot de passe</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              disabled={pending}
              className="rounded-lg border border-cyan-500/30 bg-slate-950/80 px-3 py-2.5 text-cyan-50 outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/40"
            />
          </label>

          {error && (
            <div className="rounded-lg border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-sm text-orange-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={pending || !username || !password}
            className="mt-2 rounded-full bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-cyan-500/40"
          >
            {pending ? "Connexion…" : "Se connecter"}
          </button>

          <p className="text-center text-[10px] uppercase tracking-widest text-cyan-700/60">
            Session 4 h · accès réservé
          </p>
        </form>
      </section>
    </main>
  );
}
