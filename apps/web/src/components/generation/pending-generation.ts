import type { GenerationMode } from "@ai-music-studio/shared";

export type PendingGenerationState = "queued" | "running" | "failed";

export interface PendingGeneration {
  id: string;
  trackId: string | null;
  prompt: string;
  style: string | null;
  negativeTags: string | null;
  makeInstrumental: boolean;
  generationMode: GenerationMode;
  parentTrackId: string | null;
  audioWeight: number | null;
  continueAtSec: number | null;
  state: PendingGenerationState;
  error: string | null;
}
