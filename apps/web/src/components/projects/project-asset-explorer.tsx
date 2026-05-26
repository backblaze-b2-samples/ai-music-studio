"use client";

import { FolderOpen } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjectAssets } from "@/lib/queries";

interface Props {
  projectId: string;
}

/**
 * Project-scoped asset explorer.
 *
 * Scoped to `prefix="projects/<id>/"` and rendered inside the project
 * page. The global `/files` route keeps the full-bucket tree view for
 * ops-style browsing (see AGENTS.md repository map).
 *
 * Intentionally simple — a flat newest-first list, not a recursive tree.
 * The full-bucket explorer handles the tree-view UX; for a project's
 * scoped slice a flat list is plenty (~tens of objects).
 */
export function ProjectAssetExplorer({ projectId }: Props) {
  const { data, isLoading, error, refetch } = useProjectAssets(projectId);

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

  const files = data ?? [];

  if (files.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={FolderOpen}
            title="No files yet"
            description="Generated tracks and uploaded reference clips will appear here."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="card-title flex items-center gap-2">
          <FolderOpen className="h-4 w-4" />
          Project files
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Everything stored under{" "}
          <code className="font-mono">projects/{projectId.slice(0, 8)}…/</code>{" "}
          in B2. The full-bucket view is at <code className="font-mono">/files</code>.
        </p>
      </CardHeader>
      <CardContent>
        <ul className="divide-y divide-border text-sm">
          {files.map((f) => (
            <li
              key={f.key}
              className="flex items-center justify-between py-2 gap-3"
            >
              <code className="font-mono text-xs truncate flex-1 min-w-0">
                {f.key}
              </code>
              <span className="text-xs text-muted-foreground tabular-nums">
                {f.size_human}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
