"use client";

import { type ReactNode, useState } from "react";
import { GitBranch, Repeat, Sparkles, Wand2, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api-client";
import { useGenerate } from "@/lib/queries";
import type { GenerationMode, Track } from "@ai-music-studio/shared";

import type { PendingGeneration } from "./pending-generation";

interface GenerateFormProps {
  projectId: string;
  parentTrack: Track | null;
  onClearBranch: () => void;
  onGenerationFailed: (id: string, error: string) => void;
  onGenerationStart: (pending: PendingGeneration) => void;
  onGenerationSuccess: (id: string, trackId: string) => void;
}

function defaultContinueAtSec(parentTrack: Track | null): number {
  return parentTrack?.audio.duration_ms
    ? Math.round(parentTrack.audio.duration_ms / 1000)
    : 0;
}

function pendingGenerationId(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `pending-${Date.now()}`;
}

export function GenerateForm({
  projectId,
  parentTrack,
  onClearBranch,
  onGenerationFailed,
  onGenerationStart,
  onGenerationSuccess,
}: GenerateFormProps) {
  const generate = useGenerate(projectId);
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("");
  const [negativeTags, setNegativeTags] = useState("");
  const [makeInstrumental, setMakeInstrumental] = useState(false);
  const [generationMode, setGenerationMode] = useState<GenerationMode>(
    parentTrack ? "new_take" : "create",
  );
  const [continueAtSec, setContinueAtSec] = useState(
    defaultContinueAtSec(parentTrack),
  );
  const [audioWeight, setAudioWeight] = useState(0.6);
  const parentTrackId = parentTrack?.track_id ?? null;
  const providerBranchReady = !!parentTrack?.provider_clip_id;

  const selectProviderBranchMode = (mode: Extract<GenerationMode, "extend" | "restyle">) => {
    if (!providerBranchReady) {
      toast.error(
        "Extend and Restyle need a MusicAPI clip id. Generate a fresh parent track first.",
      );
      return;
    }
    setGenerationMode(mode);
  };

  const submit = () => {
    if (!prompt.trim()) {
      toast.error("Prompt is required");
      return;
    }
    if (generationMode === "extend" && continueAtSec < 0) {
      toast.error("Extend timestamp must be zero or greater");
      return;
    }
    if (generationMode === "restyle" && (audioWeight < 0 || audioWeight > 1)) {
      toast.error("Source influence must be between 0 and 1");
      return;
    }
    const request = {
      prompt: prompt.trim(),
      style: style.trim() || null,
      negative_tags: negativeTags.trim() || null,
      make_instrumental: makeInstrumental,
      generation_mode: parentTrack ? generationMode : "create",
      continue_at_sec: generationMode === "extend" ? continueAtSec : null,
      audio_weight: generationMode === "restyle" ? audioWeight : null,
      parent_track_id: parentTrackId,
    };
    const pendingId = pendingGenerationId();
    onGenerationStart({
      id: pendingId,
      prompt: request.prompt,
      style: request.style,
      negativeTags: request.negative_tags,
      makeInstrumental: request.make_instrumental,
      generationMode: request.generation_mode,
      parentTrackId: request.parent_track_id,
      audioWeight: request.audio_weight,
      continueAtSec: request.continue_at_sec,
      state: "queued",
      trackId: null,
      error: null,
    });
    generate.mutate(
      request,
      {
        onSuccess: (status) => {
          onGenerationSuccess(pendingId, status.track_id);
          toast.success(parentTrackId ? "Branch queued" : "Generation queued");
          setPrompt("");
        },
        onError: (err) => {
          const msg = err instanceof ApiError ? err.message : "Generation failed";
          onGenerationFailed(pendingId, msg);
          toast.error(msg);
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="card-title">
            {parentTrackId ? "Branch from selected track" : "Generate a track"}
          </CardTitle>
          {parentTrackId && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={onClearBranch}
            >
              <X className="h-3 w-3 mr-1" />
              Clear branch
            </Button>
          )}
        </div>
        {parentTrackId && (
          <p className="text-xs text-muted-foreground inline-flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            parent: <code className="font-mono">{parentTrackId.slice(0, 8)}…</code>
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="prompt">Prompt</Label>
          <Textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="A warm ambient pad with soft bells and a slow tempo."
            rows={3}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="style">Style</Label>
          <Input
            id="style"
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            placeholder="dreamy synth-pop, warm analog, neon, mid-tempo"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <div className="space-y-1.5">
            <Label htmlFor="negative-tags">Avoid</Label>
            <Input
              id="negative-tags"
              value={negativeTags}
              onChange={(e) => setNegativeTags(e.target.value)}
              placeholder="country, acoustic, spoken word"
            />
          </div>
          <div className="flex h-10 items-center gap-2 rounded-md border border-border px-3">
            <Switch
              id="make-instrumental"
              checked={makeInstrumental}
              onCheckedChange={setMakeInstrumental}
            />
            <Label htmlFor="make-instrumental" className="text-sm">
              Instrumental
            </Label>
          </div>
        </div>
        {parentTrack && (
          <div className="space-y-3">
            <div className="grid gap-2 sm:grid-cols-3">
              <BranchModeButton
                active={generationMode === "new_take"}
                icon={<Sparkles className="h-3.5 w-3.5" />}
                label="New take"
                onClick={() => setGenerationMode("new_take")}
              />
              <BranchModeButton
                active={generationMode === "extend"}
                icon={<Repeat className="h-3.5 w-3.5" />}
                label="Extend"
                title="Continue this track from a timestamp"
                onClick={() => selectProviderBranchMode("extend")}
              />
              <BranchModeButton
                active={generationMode === "restyle"}
                icon={<Wand2 className="h-3.5 w-3.5" />}
                label="Restyle"
                title="Create a stylistic cover from this track"
                onClick={() => selectProviderBranchMode("restyle")}
              />
            </div>
            {generationMode === "extend" && (
              <div className="space-y-1.5">
                <Label htmlFor="continue-at">Extend from (sec)</Label>
                <Input
                  id="continue-at"
                  type="number"
                  min={0}
                  value={continueAtSec}
                  onChange={(e) =>
                    setContinueAtSec(Number.parseInt(e.target.value || "0", 10))
                  }
                />
              </div>
            )}
            {generationMode === "restyle" && (
              <div className="space-y-1.5">
                <Label htmlFor="audio-weight">Source influence</Label>
                <Input
                  id="audio-weight"
                  type="number"
                  min={0}
                  max={1}
                  step={0.1}
                  value={audioWeight}
                  onChange={(e) =>
                    setAudioWeight(Number.parseFloat(e.target.value || "0"))
                  }
                />
              </div>
            )}
          </div>
        )}
        <div className="flex items-center justify-end gap-2">
          <Button onClick={submit} disabled={generate.isPending}>
            <Sparkles className="h-3.5 w-3.5 mr-1" />
            {generate.isPending ? "Queueing..." : "Generate"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function BranchModeButton({
  active,
  icon,
  label,
  title,
  onClick,
}: {
  active: boolean;
  icon: ReactNode;
  label: string;
  title?: string;
  onClick: () => void;
}) {
  return (
    <Button
      type="button"
      variant={active ? "default" : "outline"}
      className="h-8 justify-center gap-1.5 text-xs"
      title={title}
      onClick={onClick}
    >
      {icon}
      {label}
    </Button>
  );
}
