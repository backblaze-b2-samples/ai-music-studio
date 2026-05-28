"use client";

import { useState } from "react";
import { Download, GitBranch, GitCompare, Layers, Play, Wrench } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ApiError,
  getTrackDownloadUrl,
  getTrackPlaybackUrl,
} from "@/lib/api-client";
import { useRepairTrackSidecar, useSplitTrackStems } from "@/lib/queries";
import type { Track } from "@ai-music-studio/shared";

interface TrackNodeProps {
  projectId: string;
  track: Track;
  onBranch: (track: Track) => void;
  onPickCompareA: (trackId: string) => void;
  onPickCompareB: (trackId: string) => void;
  compareA: string | null;
  compareB: string | null;
}

function formatDuration(ms: number | null | undefined): string {
  if (!ms) return "—";
  const seconds = Math.round(ms / 1000);
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function modeLabel(mode: Track["generation_mode"]): string | null {
  if (mode === "extend") return "extend";
  if (mode === "restyle") return "restyle";
  if (mode === "new_take") return "new take";
  return null;
}

export function TrackNode({
  projectId,
  track,
  onBranch,
  onPickCompareA,
  onPickCompareB,
  compareA,
  compareB,
}: TrackNodeProps) {
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const repairMutation = useRepairTrackSidecar(projectId);
  const splitStemsMutation = useSplitTrackStems(projectId);

  const isA = compareA === track.track_id;
  const isB = compareB === track.track_id;
  const branchLabel = modeLabel(track.generation_mode);

  const play = async () => {
    setLoading(true);
    try {
      const { url } = await getTrackPlaybackUrl(projectId, track.track_id);
      setAudioSrc(url);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Could not load track";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const download = async () => {
    try {
      const { url } = await getTrackDownloadUrl(projectId, track.track_id);
      window.open(url, "_blank");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Download failed";
      toast.error(msg);
    }
  };

  const repair = () => {
    repairMutation.mutate(track.track_id, {
      onSuccess: () => toast.success("Track sidecar repaired"),
      onError: (err) => {
        const msg = err instanceof ApiError ? err.message : "Repair failed";
        toast.error(msg);
      },
    });
  };

  const splitStems = () => {
    splitStemsMutation.mutate(track.track_id, {
      onSuccess: (stems) => toast.success(`Generated ${stems.length} stems`),
      onError: (err) => {
        const msg =
          err instanceof ApiError ? err.message : "Stem generation failed";
        toast.error(msg);
      },
    });
  };

  return (
    <Card
      className={
        isA || isB
          ? "ring-2 ring-primary border-primary/50"
          : ""
      }
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 mb-1">
              <code className="text-[10px] font-mono text-muted-foreground">
                {track.track_id.slice(0, 8)}…
              </code>
              <Badge variant="outline" className="h-4 px-1.5 text-[10px]">
                {track.provider}
              </Badge>
              {track.make_instrumental && (
                <Badge variant="outline" className="h-4 px-1.5 text-[10px]">
                  instrumental
                </Badge>
              )}
              {track.is_orphaned && (
                <Badge variant="destructive" className="h-4 px-1.5 text-[10px]">
                  orphan
                </Badge>
              )}
              {track.parent_track_id && (
                <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
                  <GitBranch className="h-2.5 w-2.5 mr-0.5" />
                  {branchLabel ?? "branch"}
                </Badge>
              )}
              {isA && (
                <Badge className="h-4 px-1.5 text-[10px] bg-primary">A</Badge>
              )}
              {isB && (
                <Badge className="h-4 px-1.5 text-[10px] bg-primary">B</Badge>
              )}
            </div>
            <p className="text-sm font-medium line-clamp-2">{track.prompt}</p>
            <p className="text-xs text-muted-foreground mt-1 tabular-nums">
              {track.style ?? "—"} · {formatDuration(track.audio.duration_ms)} ·{" "}
              {track.audio.codec ?? "?"} ·{" "}
              {track.generation_ms ? `${track.generation_ms}ms gen` : "—"}
            </p>
            {track.negative_tags && (
              <p className="text-[11px] text-muted-foreground mt-1 line-clamp-1">
                Avoid: {track.negative_tags}
              </p>
            )}
            {track.generation_mode === "extend" && (
              <p className="text-[11px] text-muted-foreground mt-1">
                Extend from: {track.continue_at_sec ?? 0}s
              </p>
            )}
            {track.generation_mode === "restyle" && (
              <p className="text-[11px] text-muted-foreground mt-1">
                Source influence: {track.audio_weight ?? 0.6}
              </p>
            )}
            {track.stems_keys.length > 0 && (
              <p className="text-[11px] text-muted-foreground mt-1">
                {track.stems_keys.length} stems available
              </p>
            )}
            {track.is_orphaned && (
              <p className="text-[11px] text-destructive mt-1">
                Audio exists in B2, but track.json is missing.
              </p>
            )}
          </div>
        </div>

        {audioSrc ? (
          <audio
            controls
            autoPlay
            src={audioSrc}
            className="w-full h-9"
            onError={() => {
              setAudioSrc(null);
              toast.error("Playback failed");
            }}
          />
        ) : (
          <div className="flex flex-wrap items-center gap-1.5">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={play}
              disabled={loading}
            >
              <Play className="h-3 w-3 mr-1" />
              {loading ? "Loading..." : "Play"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={download}
            >
              <Download className="h-3 w-3 mr-1" />
              Download
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={() => onBranch(track)}
              disabled={track.is_orphaned}
            >
              <GitBranch className="h-3 w-3 mr-1" />
              Branch
            </Button>
            {track.is_orphaned && (
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={repair}
                disabled={repairMutation.isPending}
              >
                <Wrench className="h-3 w-3 mr-1" />
                {repairMutation.isPending ? "Repairing..." : "Repair"}
              </Button>
            )}
            <Button
              size="sm"
              variant={isA ? "default" : "ghost"}
              className="h-7 text-xs"
              aria-pressed={isA}
              title={isA ? "Clear compare A" : "Pick as compare A"}
              onClick={() => onPickCompareA(track.track_id)}
            >
              <GitCompare className="h-3 w-3 mr-1" />
              Compare A
            </Button>
            <Button
              size="sm"
              variant={isB ? "default" : "ghost"}
              className="h-7 text-xs"
              aria-pressed={isB}
              title={isB ? "Clear compare B" : "Pick as compare B"}
              onClick={() => onPickCompareB(track.track_id)}
            >
              <GitCompare className="h-3 w-3 mr-1" />
              Compare B
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs text-muted-foreground"
              onClick={splitStems}
              disabled={track.is_orphaned || splitStemsMutation.isPending}
              title="Run the configured stem splitter"
            >
              <Layers className="h-3 w-3 mr-1" />
              {splitStemsMutation.isPending ? "Splitting..." : "Generate Stems"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
