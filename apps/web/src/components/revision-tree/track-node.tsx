"use client";

import { useState } from "react";
import { Download, GitBranch, GitCompare, Layers, Play } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ApiError,
  getTrackDownloadUrl,
  getTrackPlaybackUrl,
} from "@/lib/api-client";
import type { Track } from "@ai-music-studio/shared";

interface TrackNodeProps {
  projectId: string;
  track: Track;
  onBranch: (trackId: string) => void;
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

  const isA = compareA === track.track_id;
  const isB = compareB === track.track_id;

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
              {track.parent_track_id && (
                <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
                  <GitBranch className="h-2.5 w-2.5 mr-0.5" />
                  branch
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
              onClick={() => onBranch(track.track_id)}
            >
              <GitBranch className="h-3 w-3 mr-1" />
              Branch
            </Button>
            <Button
              size="sm"
              variant={isA ? "default" : "ghost"}
              className="h-7 text-xs"
              onClick={() => onPickCompareA(track.track_id)}
            >
              <GitCompare className="h-3 w-3 mr-1" />A
            </Button>
            <Button
              size="sm"
              variant={isB ? "default" : "ghost"}
              className="h-7 text-xs"
              onClick={() => onPickCompareB(track.track_id)}
            >
              <GitCompare className="h-3 w-3 mr-1" />B
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs text-muted-foreground"
              disabled
              title="Stem separation is coming soon"
            >
              <Layers className="h-3 w-3 mr-1" />
              Generate Stems (coming soon)
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
