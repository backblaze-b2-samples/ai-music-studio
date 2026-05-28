"use client";

import { GitMerge } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { PendingGeneration } from "@/components/generation/pending-generation";
import { useRevisionTree } from "@/lib/queries";
import type { RevisionNode, Track } from "@ai-music-studio/shared";

import { PendingTrackNode } from "./pending-track-node";
import { TrackNode } from "./track-node";

interface RevisionTreeProps {
  projectId: string;
  pendingGeneration: PendingGeneration | null;
  onDismissPendingGeneration: () => void;
  onBranch: (track: Track) => void;
  onPickCompareA: (trackId: string) => void;
  onPickCompareB: (trackId: string) => void;
  compareA: string | null;
  compareB: string | null;
}

/**
 * Indented-list rendering of the project's revision tree. Deliberately
 * starts simple — `docs/exec-plans/tech-debt-tracker.md` tracks a future
 * d3-force / canvas upgrade if/when the tree gets visually unwieldy.
 */
export function RevisionTree({
  projectId,
  pendingGeneration,
  onDismissPendingGeneration,
  onBranch,
  onPickCompareA,
  onPickCompareB,
  compareA,
  compareB,
}: RevisionTreeProps) {
  const { data, isLoading, error, refetch } = useRevisionTree(projectId);

  if (isLoading) {
    return <Skeleton className="h-48 w-full" />;
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

  const roots = data ?? [];
  const hasPendingRoot = !!pendingGeneration && !pendingGeneration.parentTrackId;
  const pendingParentInTree = pendingGeneration?.parentTrackId
    ? treeContainsTrack(roots, pendingGeneration.parentTrackId)
    : false;

  if (roots.length === 0 && !pendingGeneration) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={GitMerge}
            title="No tracks yet"
            description="Generate your first track above to seed the revision tree."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="card-title flex items-center gap-2">
          <GitMerge className="h-4 w-4" />
          Revision tree
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {hasPendingRoot && (
          <PendingTrackNode
            pending={pendingGeneration}
            onDismiss={onDismissPendingGeneration}
          />
        )}
        {roots.map((root) => (
          <NodeRow
            key={root.track.track_id}
            projectId={projectId}
            node={root}
            depth={0}
            pendingGeneration={pendingGeneration}
            onDismissPendingGeneration={onDismissPendingGeneration}
            onBranch={onBranch}
            onPickCompareA={onPickCompareA}
            onPickCompareB={onPickCompareB}
            compareA={compareA}
            compareB={compareB}
          />
        ))}
        {pendingGeneration && pendingGeneration.parentTrackId && !pendingParentInTree && (
          <PendingTrackNode
            pending={pendingGeneration}
            onDismiss={onDismissPendingGeneration}
          />
        )}
      </CardContent>
    </Card>
  );
}

function treeContainsTrack(nodes: RevisionNode[], trackId: string): boolean {
  return nodes.some(
    (node) =>
      node.track.track_id === trackId || treeContainsTrack(node.children, trackId),
  );
}

interface NodeRowProps {
  projectId: string;
  node: RevisionNode;
  depth: number;
  pendingGeneration: PendingGeneration | null;
  onDismissPendingGeneration: () => void;
  onBranch: (track: Track) => void;
  onPickCompareA: (trackId: string) => void;
  onPickCompareB: (trackId: string) => void;
  compareA: string | null;
  compareB: string | null;
}

function NodeRow({
  projectId,
  node,
  depth,
  pendingGeneration,
  onDismissPendingGeneration,
  onBranch,
  onPickCompareA,
  onPickCompareB,
  compareA,
  compareB,
}: NodeRowProps) {
  const hasPendingChild =
    pendingGeneration?.parentTrackId === node.track.track_id;

  return (
    <div>
      <div style={{ paddingLeft: depth * 24 }}>
        <TrackNode
          projectId={projectId}
          track={node.track}
          onBranch={onBranch}
          onPickCompareA={onPickCompareA}
          onPickCompareB={onPickCompareB}
          compareA={compareA}
          compareB={compareB}
        />
      </div>
      {(hasPendingChild || node.children.length > 0) && (
        <div className="mt-3 space-y-3">
          {hasPendingChild && pendingGeneration && (
            <div style={{ paddingLeft: (depth + 1) * 24 }}>
              <PendingTrackNode
                pending={pendingGeneration}
                onDismiss={onDismissPendingGeneration}
              />
            </div>
          )}
          {node.children.map((child) => (
            <NodeRow
              key={child.track.track_id}
              projectId={projectId}
              node={child}
              depth={depth + 1}
              pendingGeneration={pendingGeneration}
              onDismissPendingGeneration={onDismissPendingGeneration}
              onBranch={onBranch}
              onPickCompareA={onPickCompareA}
              onPickCompareB={onPickCompareB}
              compareA={compareA}
              compareB={compareB}
            />
          ))}
        </div>
      )}
    </div>
  );
}
