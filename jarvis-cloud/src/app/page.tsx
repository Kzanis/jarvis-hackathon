import Link from "next/link";

export default function Landing() {
  return (
    <main className="min-h-dvh bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900 text-cyan-50">
      <section className="mx-auto flex min-h-dvh max-w-3xl flex-col items-center justify-center px-6 text-center">
        <p className="mb-3 text-xs uppercase tracking-[0.4em] text-cyan-400/80">
          Hackathon Creator Academy · 2026
        </p>
        <h1 className="text-5xl font-semibold tracking-tight text-cyan-50 sm:text-6xl">
          Jarvis
        </h1>
        <p className="mt-2 text-base font-light text-cyan-300/80 sm:text-lg">
          Majordome personnel IA — domotique, agenda, son
        </p>

        <p className="mt-8 max-w-xl text-cyan-100/80">
          Un assistant qui pilote physiquement votre maison depuis votre
          téléphone, dans le ton d&apos;un majordome britannique. Volets,
          portail, garage, alarme, son, agenda — orchestrés en langage naturel
          par un agent IA Claude.
        </p>

        <div className="mt-10 flex flex-col items-center gap-3">
          <Link
            href="/app"
            className="rounded-full bg-cyan-500 px-8 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            Ouvrir Jarvis
          </Link>
          <p className="text-xs text-cyan-700/70">
            Installez-le comme application sur votre téléphone (PWA)
          </p>
        </div>

        <footer className="mt-16 grid w-full max-w-2xl grid-cols-1 gap-6 sm:grid-cols-3">
          <Stat label="Pilote sur" value="Freebox Delta" />
          <Stat label="Cerveau" value="Claude Haiku 4.5" />
          <Stat label="Hébergement" value="Hostinger + Maison" />
        </footer>
      </section>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-cyan-500/20 bg-slate-900/40 p-4">
      <div className="text-[10px] uppercase tracking-widest text-cyan-700/80">
        {label}
      </div>
      <div className="mt-1 text-sm font-medium text-cyan-100">{value}</div>
    </div>
  );
}
