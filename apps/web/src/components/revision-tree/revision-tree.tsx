"use client";

import { GitMerge } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useRevisionTree } from "@/lib/queries";
import type { RevisionNode } from "@ai-music-studio/shared";

import { TrackNode } from "./track-node";

interface RevisionTreeProps {
  projectId: string;
  onBranch: (trackId: string) => void;
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

  if (roots.length === 0) {
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
        {roots.map((root) => (
          <NodeRow
            key={root.track.track_id}
            projectId={projectId}
            node={root}
            depth={0}
            onBranch={onBranch}
            onPickCompareA={onPickCompareA}
            onPickCompareB={onPickCompareB}
            compareA={compareA}
            compareB={compareB}
          />
        ))}
      </CardContent>
    </Card>
  );
}

interface NodeRowProps {
  projectId: string;
  node: RevisionNode;
  depth: number;
  onBranch: (trackId: string) => void;
  onPickCompareA: (trackId: string) => void;
  onPickCompareB: (trackId: string) => void;
  compareA: string | null;
  compareB: string | null;
}

function NodeRow({
  projectId,
  node,
  depth,
  onBranch,
  onPickCompareA,
  onPickCompareB,
  compareA,
  compareB,
}: NodeRowProps) {
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
      {node.children.length > 0 && (
        <div className="mt-3 space-y-3">
          {node.children.map((child) => (
            <NodeRow
              key={child.track.track_id}
              projectId={projectId}
              node={child}
              depth={depth + 1}
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
