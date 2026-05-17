"use client";

import { useEffect, useRef } from "react";

import { useJarvis } from "@/lib/store";

export function Transcript() {
  const transcript = useJarvis((s) => s.transcript);
  const lastError = useJarvis((s) => s.lastError);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [transcript, lastError]);

  if (transcript.length === 0 && !lastError) {
    return (
      <div className="rounded-lg border border-cyan-500/20 bg-slate-900/40 p-6 text-center text-cyan-700/70">
        Adressez-vous à Jarvis. Vos échanges apparaîtront ici.
      </div>
    );
  }

  return (
    <div className="flex max-h-72 flex-col gap-2 overflow-y-auto rounded-lg border border-cyan-500/20 bg-slate-900/40 p-4">
      {transcript.map((entry, i) => (
        <div
          key={`${entry.timestamp}-${i}`}
          className={
            entry.role === "user"
              ? "self-end max-w-[80%] rounded-lg bg-cyan-500/20 px-3 py-2 text-cyan-100"
              : "self-start max-w-[80%] rounded-lg bg-slate-800/60 px-3 py-2 text-cyan-50"
          }
        >
          <div className="mb-0.5 text-[10px] uppercase tracking-wide text-cyan-700/80">
            {entry.role === "user" ? "Vous" : "Jarvis"}
          </div>
          <div className="text-sm leading-relaxed">{entry.content}</div>
        </div>
      ))}
      {lastError && (
        <div className="self-start max-w-[90%] rounded-lg border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-orange-200">
          <div className="text-[10px] uppercase tracking-wide">Erreur</div>
          <div className="text-sm">{lastError}</div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
