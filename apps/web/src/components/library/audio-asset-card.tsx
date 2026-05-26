"use client";

import { useState } from "react";
import { Download, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Waveform } from "./waveform";
import { ApiError, getLibraryDownloadUrl, getPlaybackUrl } from "@/lib/api-client";
import { useDeleteAudioAsset } from "@/lib/queries";
import { formatDate, formatDuration } from "@/lib/utils";
import type { AudioAsset } from "@ai-music-studio/shared";

interface AudioAssetCardProps {
  asset: AudioAsset;
  selected?: boolean;
  onToggleSelect?: (key: string) => void;
}

/**
 * The default Library primitive for audio samples on this kit.
 *
 * Renders an audio asset with a metadata strip (duration · sample rate ·
 * channels · created date), an inline waveform stub, and Play / Download /
 * Delete actions. Play swaps the action row for a native `<audio controls>`
 * fed by a short-lived presigned URL. Delete is gated by an AlertDialog.
 */
export function AudioAssetCard({
  asset,
  selected = false,
  onToggleSelect,
}: AudioAssetCardProps) {
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [loadingPlayback, setLoadingPlayback] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const deleteMutation = useDeleteAudioAsset();

  const handlePlay = async () => {
    if (audioSrc) return;
    setLoadingPlayback(true);
    try {
      const { url } = await getPlaybackUrl(asset.key);
      setAudioSrc(url);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to load playback URL";
      toast.error(detail);
    } finally {
      setLoadingPlayback(false);
    }
  };

  const handleDownload = async () => {
    try {
      const { url } = await getLibraryDownloadUrl(asset.key);
      window.open(url, "_blank");
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to get download URL";
      toast.error(detail);
    }
  };

  const handleDelete = () => {
    deleteMutation.mutate(asset.key, {
      onSuccess: () => {
        toast.success("Audio asset deleted");
        setConfirmDelete(false);
      },
      onError: (err) => {
        const detail = err instanceof ApiError ? err.message : "Failed to delete";
        toast.error(detail);
      },
    });
  };

  const metaParts: string[] = [];
  if (asset.duration_ms) metaParts.push(formatDuration(asset.duration_ms));
  if (asset.sample_rate) metaParts.push(`${(asset.sample_rate / 1000).toFixed(1)} kHz`);
  if (asset.channels) {
    metaParts.push(asset.channels === 1 ? "mono" : `${asset.channels} ch`);
  }
  metaParts.push(formatDate(asset.created_at));

  return (
    <>
      <Card
        className={`card-hover ${selected ? "ring-2 ring-primary" : ""}`}
      >
        <CardContent className="space-y-3 p-4">
          <div className="flex items-start justify-between gap-3">
            {onToggleSelect && (
              <Checkbox
                checked={selected}
                onCheckedChange={() => onToggleSelect(asset.key)}
                aria-label={`Select ${asset.title_preview ?? asset.key}`}
                className="mt-1"
              />
            )}
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-sm font-medium font-mono">
                {asset.title_preview ?? asset.key.split("/").pop()}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {metaParts.join(" · ")}
              </p>
            </div>
          </div>

          <Waveform durationMs={asset.duration_ms} />

          {audioSrc ? (
            <audio controls src={audioSrc} className="w-full" autoPlay />
          ) : (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handlePlay}
                disabled={loadingPlayback}
              >
                <Play className="h-3.5 w-3.5" />
                {loadingPlayback ? "Loading..." : "Play"}
              </Button>
              <Button size="sm" variant="outline" onClick={handleDownload}>
                <Download className="h-3.5 w-3.5" />
                Download
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setConfirmDelete(true)}
                className="ml-auto text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete audio asset?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes <code className="font-mono">{asset.key}</code> from B2. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
