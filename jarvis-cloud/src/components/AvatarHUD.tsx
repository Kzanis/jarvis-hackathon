"use client";

/**
 * Avatar HUD Jarvis — Canvas 2D inspiré du HUD J.A.R.V.I.S. d'Iron Man.
 *
 * 6 états visuels : idle / listening / thinking / speaking / action / error.
 * - Cercles concentriques cyan qui pulsent
 * - Anneau d'amplitude audio (lip-sync) en mode speaking, alimenté par
 *   un AudioBuffer source via Web Audio API (à brancher Phase B+)
 *
 * Volontairement compact (~280 lignes) pour démarrer ; on enrichira plus tard.
 */

import { useEffect, useRef } from "react";

import type { JarvisState } from "@/lib/store";

interface Props {
  state: JarvisState;
  /** Amplitude audio en cours (0..1) pour le lip-sync en mode speaking. */
  amplitude?: number;
  size?: number;
}

const COLORS = {
  idle: { primary: "#22d3ee", secondary: "#0e7490", glow: "#22d3ee" },
  listening: { primary: "#38bdf8", secondary: "#0369a1", glow: "#38bdf8" },
  thinking: { primary: "#a78bfa", secondary: "#5b21b6", glow: "#a78bfa" },
  speaking: { primary: "#22d3ee", secondary: "#0891b2", glow: "#06b6d4" },
  action: { primary: "#4ade80", secondary: "#15803d", glow: "#4ade80" },
  error: { primary: "#f97316", secondary: "#9a3412", glow: "#fb923c" },
} as const;

export function AvatarHUD({ state, amplitude = 0, size = 280 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const stateRef = useRef(state);
  const amplitudeRef = useRef(amplitude);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  useEffect(() => {
    amplitudeRef.current = amplitude;
  }, [amplitude]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);

    const cx = size / 2;
    const cy = size / 2;

    let start = performance.now();

    const draw = (now: number) => {
      const t = (now - start) / 1000;
      const currentState = stateRef.current;
      const amp = amplitudeRef.current;
      const colors = COLORS[currentState];

      ctx.clearRect(0, 0, size, size);

      // Fond glow doux
      const radialGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, size / 2);
      radialGrad.addColorStop(0, `${colors.glow}22`);
      radialGrad.addColorStop(1, "transparent");
      ctx.fillStyle = radialGrad;
      ctx.fillRect(0, 0, size, size);

      // 3 anneaux concentriques
      const baseRadius = size * 0.28;
      const pulse =
        currentState === "listening"
          ? 0.08 * Math.sin(t * 7)
          : currentState === "thinking"
          ? 0.05 * Math.sin(t * 3)
          : currentState === "speaking"
          ? 0.04 + amp * 0.18
          : currentState === "action"
          ? Math.max(0, 0.12 * (1 - ((t * 2) % 1)))
          : currentState === "error"
          ? 0.06 * Math.sin(t * 10)
          : 0.03 * Math.sin(t * 1.5);

      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        const r = baseRadius * (1 + i * 0.15) * (1 + pulse);
        ctx.strokeStyle = i === 1 ? colors.primary : colors.secondary;
        ctx.lineWidth = i === 1 ? 2.2 : 1;
        ctx.globalAlpha = 0.55 - i * 0.12;
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // Anneau rotatif (mode thinking)
      if (currentState === "thinking") {
        ctx.beginPath();
        const rotR = baseRadius * 1.45;
        ctx.strokeStyle = colors.primary;
        ctx.lineWidth = 2;
        const startA = t * 1.8;
        ctx.arc(cx, cy, rotR, startA, startA + Math.PI * 1.2);
        ctx.stroke();
      }

      // Tirets autour (style HUD)
      ctx.strokeStyle = colors.primary;
      ctx.lineWidth = 2;
      const dashRadius = baseRadius * 1.7;
      for (let k = 0; k < 12; k++) {
        const angle = (k / 12) * Math.PI * 2 + t * 0.2;
        const x1 = cx + Math.cos(angle) * dashRadius;
        const y1 = cy + Math.sin(angle) * dashRadius;
        const x2 = cx + Math.cos(angle) * (dashRadius + 12);
        const y2 = cy + Math.sin(angle) * (dashRadius + 12);
        ctx.globalAlpha = 0.4 + 0.4 * Math.sin(t * 2 + k);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // Coeur central : disque pulsé + œil cyclope HUD
      ctx.beginPath();
      const innerRadius = baseRadius * 0.4 * (1 + pulse * 0.5);
      const innerGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, innerRadius);
      innerGrad.addColorStop(0, colors.glow);
      innerGrad.addColorStop(0.6, `${colors.primary}cc`);
      innerGrad.addColorStop(1, `${colors.secondary}40`);
      ctx.fillStyle = innerGrad;
      ctx.arc(cx, cy, innerRadius, 0, Math.PI * 2);
      ctx.fill();

      // Barre amplitude (lip-sync simplifié) en mode speaking
      if (currentState === "speaking") {
        const barWidth = baseRadius * 0.9 * (0.4 + amp * 0.6);
        const barHeight = 4 + amp * 14;
        ctx.fillStyle = colors.glow;
        ctx.fillRect(cx - barWidth / 2, cy - barHeight / 2, barWidth, barHeight);
      }

      // Label state
      ctx.fillStyle = colors.primary;
      ctx.font = "600 11px ui-sans-serif, system-ui";
      ctx.textAlign = "center";
      ctx.globalAlpha = 0.75;
      ctx.fillText(currentState.toUpperCase(), cx, size - 14);
      ctx.globalAlpha = 1;

      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [size]);

  return <canvas ref={canvasRef} aria-label="Avatar Jarvis HUD" />;
}
