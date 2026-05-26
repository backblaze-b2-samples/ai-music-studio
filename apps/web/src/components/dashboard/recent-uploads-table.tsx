"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Inbox, Play } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ApiError, getPlaybackUrl } from "@/lib/api-client";
import { useLibrary } from "@/lib/queries";
import { formatDate, formatDuration } from "@/lib/utils";
import type { AudioAsset } from "@ai-music-studio/shared";

/**
 * Audio-first recent uploads table for the dashboard.
 *
 * Sources rows from `useLibrary` (audio prefix only — not the full bucket),
 * renders duration / format / date, and lets the user preview a track inline
 * via a small Dialog holding a native `<audio controls>` fed by a short-lived
 * presigned URL from `getPlaybackUrl`. The loading/error toast pattern mirrors
 * `components/library/audio-asset-card.tsx` for consistency.
 */
export function RecentUploadsTable() {
  const { data: assets = [], isLoading, error, refetch } = useLibrary(10);
  const [activeAsset, setActiveAsset] = useState<AudioAsset | null>(null);
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const handlePlay = async (asset: AudioAsset) => {
    setLoadingKey(asset.key);
    try {
      const { url } = await getPlaybackUrl(asset.key);
      setAudioSrc(url);
      setActiveAsset(asset);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to load playback URL";
      toast.error(detail);
    } finally {
      setLoadingKey(null);
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setActiveAsset(null);
      setAudioSrc(null);
    }
  };

  const filenameFor = (asset: AudioAsset) =>
    asset.title_preview ?? asset.key.split("/").pop() ?? asset.key;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Tracks</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/library"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : assets.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No tracks yet"
            description="Generate a track in a project to see it here."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[38%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Filename
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Duration
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Format
                </TableHead>
                <TableHead className="w-[22%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Date
                </TableHead>
                <TableHead className="w-[12%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <span className="sr-only">Play</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {assets.map((asset) => (
                <TableRow key={asset.key} className="table-row-hover">
                  <TableCell className="font-medium">
                    <div className="truncate">{filenameFor(asset)}</div>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {formatDuration(asset.duration_ms)}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap uppercase text-xs">
                    {asset.codec ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatDate(asset.created_at)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handlePlay(asset)}
                      disabled={loadingKey === asset.key}
                      aria-label={`Play ${filenameFor(asset)}`}
                    >
                      <Play className="h-3.5 w-3.5" />
                      {loadingKey === asset.key ? "Loading..." : "Play"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={activeAsset !== null} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="truncate font-mono text-sm">
              {activeAsset ? filenameFor(activeAsset) : ""}
            </DialogTitle>
          </DialogHeader>
          {audioSrc ? (
            <audio controls autoPlay src={audioSrc} className="w-full" />
          ) : null}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
