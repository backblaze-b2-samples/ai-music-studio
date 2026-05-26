"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ApiError,
  getTrackPlaybackUrl,
} from "@/lib/api-client";
import { useCompare } from "@/lib/queries";
import type { Track } from "@ai-music-studio/shared";

interface CompareDialogProps {
  projectId: string;
  a: string | null;
  b: string | null;
  onClose: () => void;
}

export function CompareDialog({ projectId, a, b, onClose }: CompareDialogProps) {
  const open = !!a && !!b && a !== b;
  const { data, isLoading, error } = useCompare(projectId, a ?? undefined, b ?? undefined);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Compare tracks</DialogTitle>
          <DialogDescription>
            Side-by-side A/B with prompt, style, duration, and audio-metadata diffs.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : error ? (
          <p className="text-sm text-destructive">
            {error instanceof ApiError ? error.message : "Compare failed"}
          </p>
        ) : data ? (
          <div className="grid grid-cols-2 gap-4">
            <TrackPanel projectId={projectId} track={data.a} label="A" />
            <TrackPanel projectId={projectId} track={data.b} label="B" />
            <div className="col-span-2 text-xs text-muted-foreground border-t border-border pt-3">
              <DiffRow label="Prompt" changed={data.prompt_changed} />
              <DiffRow label="Style" changed={data.style_changed} />
              <DiffRow label="Duration" changed={data.duration_changed} />
              <DiffRow label="Audio metadata" changed={data.audio_metadata_changed} />
            </div>
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DiffRow({ label, changed }: { label: string; changed: boolean }) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      <span
        className={
          changed
            ? "inline-block h-1.5 w-1.5 rounded-full bg-attention"
            : "inline-block h-1.5 w-1.5 rounded-full bg-success"
        }
      />
      <span>
        {label}: <span className="font-medium">{changed ? "different" : "same"}</span>
      </span>
    </div>
  );
}

function TrackPanel({
  projectId,
  track,
  label,
}: {
  projectId: string;
  track: Track;
  label: string;
}) {
  const [audioSrc, setAudioSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getTrackPlaybackUrl(projectId, track.track_id)
      .then(({ url }) => {
        if (!cancelled) setAudioSrc(url);
      })
      .catch((err) => {
        if (!cancelled) {
          const msg = err instanceof ApiError ? err.message : "Playback failed";
          toast.error(msg);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, track.track_id]);

  return (
    <div className="space-y-2 border border-border rounded-md p-3">
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center justify-center h-5 w-5 rounded bg-primary text-primary-foreground text-xs font-semibold">
          {label}
        </span>
        <code className="text-[10px] font-mono text-muted-foreground">
          {track.track_id.slice(0, 8)}…
        </code>
      </div>
      <p className="text-xs line-clamp-3">{track.prompt}</p>
      <p className="text-[11px] text-muted-foreground tabular-nums">
        {track.style ?? "—"} · {track.duration_sec}s
      </p>
      {audioSrc ? (
        <audio controls src={audioSrc} className="w-full h-9" />
      ) : (
        <Skeleton className="h-9 w-full" />
      )}
    </div>
  );
}
