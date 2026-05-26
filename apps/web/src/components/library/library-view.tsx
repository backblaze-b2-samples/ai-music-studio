"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Library, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

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
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { useBulkDeleteAudioAssets, useLibrary } from "@/lib/queries";
import { AudioAssetCard } from "./audio-asset-card";

/**
 * Grid view of the audio Library — every audio asset under the `audio/`
 * prefix. Sample-specific; the full bucket lives at `/files`.
 */
export function LibraryView() {
  const { data, isLoading, isFetching, error, refetch } = useLibrary();
  const bulkDelete = useBulkDeleteAudioAssets();
  const assets = useMemo(() => data ?? [], [data]);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);

  const availableKeys = useMemo(
    () => new Set(assets.map((a) => a.key)),
    [assets],
  );

  // Drop stale selections after a refetch (e.g. after bulk delete completes).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected((prev) => {
      let changed = false;
      const next = new Set<string>();
      for (const k of prev) {
        if (availableKeys.has(k)) next.add(k);
        else changed = true;
      }
      return changed ? next : prev;
    });
  }, [availableKeys]);

  const toggleSelect = useCallback((key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelected((prev) => {
      if (prev.size === assets.length) return new Set();
      return new Set(assets.map((a) => a.key));
    });
  }, [assets]);

  const clear = useCallback(() => setSelected(new Set()), []);

  const confirmBulkDelete = () => {
    const keys = Array.from(selected);
    if (keys.length === 0) return;
    bulkDelete.mutate(keys, {
      onSuccess: (result) => {
        const ok = result.deleted.length;
        const failed = result.errors.length;
        if (failed === 0) {
          toast.success(`Deleted ${ok} ${ok === 1 ? "asset" : "assets"}`);
        } else if (ok === 0) {
          toast.error(`Failed to delete ${failed} ${failed === 1 ? "asset" : "assets"}`);
        } else {
          toast.warning(`Deleted ${ok} of ${ok + failed} — ${failed} failed`);
        }
        clear();
      },
      onError: (err) => {
        const detail = err instanceof ApiError ? err.message : "Failed to delete";
        toast.error(detail);
      },
      onSettled: () => setConfirmOpen(false),
    });
  };

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-44 w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }
  if (assets.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={Library}
            title="Nothing here yet"
            description="Generate a track from a project to see it appear in the cross-project library."
          />
        </CardContent>
      </Card>
    );
  }

  const selectedCount = selected.size;
  const allSelected = selectedCount === assets.length;
  const someSelected = selectedCount > 0 && !allSelected;

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Checkbox
              checked={allSelected ? true : someSelected ? "indeterminate" : false}
              onCheckedChange={toggleSelectAll}
              aria-label="Select all"
            />
            <span className="text-xs text-muted-foreground">
              {selectedCount > 0
                ? `${selectedCount} selected`
                : `Select all (${assets.length})`}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {selectedCount > 0 && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clear}
                  className="h-7 text-xs"
                >
                  Clear
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setConfirmOpen(true)}
                  className="h-7 text-xs"
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1" />
                  Delete
                </Button>
              </>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
              className="h-7 text-xs"
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1 ${isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {assets.map((asset) => (
            <AudioAssetCard
              key={asset.key}
              asset={asset}
              selected={selected.has(asset.key)}
              onToggleSelect={toggleSelect}
            />
          ))}
        </div>
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {selectedCount} {selectedCount === 1 ? "asset" : "assets"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the selected
              {selectedCount === 1 ? " asset" : " assets"} from B2. This cannot
              be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmBulkDelete}
              disabled={bulkDelete.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {bulkDelete.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
