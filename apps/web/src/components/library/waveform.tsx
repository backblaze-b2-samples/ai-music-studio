"use client";

import { useMemo } from "react";

interface WaveformProps {
  samples?: Float32Array | null;
  durationMs?: number | null;
  className?: string;
}

/**
 * Lightweight inline waveform.
 *
 * - When `samples` is provided we downsample to ~120 bars and render
 *   them as SVG rects so the visual reflects the actual audio.
 * - When only `durationMs` is provided (the typical library case — we
 *   don't load the audio bytes until the user clicks Play) we draw a
 *   stub pattern keyed to the duration. The pattern is deterministic
 *   for the same duration so the library doesn't shimmer between
 *   re-renders.
 */
export function Waveform({ samples, durationMs, className }: WaveformProps) {
  const bars = useMemo(() => {
    if (samples && samples.length > 0) {
      return downsample(samples, 120);
    }
    const count = 120;
    const seed = Math.max(durationMs ?? 0, 800);
    return Array.from({ length: count }, (_, i) => {
      const t = (i / count) * Math.PI * 2;
      return 0.25 + 0.45 * Math.abs(Math.sin(t * (seed % 7 || 3)));
    });
  }, [samples, durationMs]);

  return (
    <svg
      role="img"
      aria-label="Audio waveform"
      viewBox="0 0 120 40"
      preserveAspectRatio="none"
      className={className ?? "h-10 w-full text-primary/70"}
    >
      {bars.map((value, i) => {
        const h = Math.max(2, value * 36);
        const y = (40 - h) / 2;
        return (
          <rect
            key={i}
            x={i}
            y={y}
            width={0.6}
            height={h}
            fill="currentColor"
            rx={0.3}
          />
        );
      })}
    </svg>
  );
}

function downsample(samples: Float32Array, bins: number): number[] {
  const out: number[] = new Array(bins);
  const step = Math.floor(samples.length / bins);
  for (let i = 0; i < bins; i++) {
    let peak = 0;
    for (let j = 0; j < step; j++) {
      const v = Math.abs(samples[i * step + j] || 0);
      if (v > peak) peak = v;
    }
    out[i] = peak;
  }
  return out;
}
