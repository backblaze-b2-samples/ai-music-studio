"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { GenerateForm } from "@/components/generation/generate-form";
import type { PendingGeneration } from "@/components/generation/pending-generation";
import { CompareDialog } from "@/components/revision-tree/compare-dialog";
import { RevisionTree } from "@/components/revision-tree/revision-tree";
import { ProjectAssetExplorer } from "@/components/projects/project-asset-explorer";
import { UploadForm } from "@/components/upload/upload-form";
import { qk, useGenerationStatus, useProject } from "@/lib/queries";
import type { Track } from "@ai-music-studio/shared";

interface ProjectDetailProps {
  projectId: string;
}

export function ProjectDetail({ projectId }: ProjectDetailProps) {
  const { data, isLoading, error, refetch } = useProject(projectId);
  // Branching seed: when set, the next generation lands as a child of this track.
  const [branchFromTrack, setBranchFromTrack] = useState<Track | null>(null);
  // Compare seed: a + b
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);
  const [pendingGeneration, setPendingGeneration] =
    useState<PendingGeneration | null>(null);
  const qc = useQueryClient();
  const status = useGenerationStatus(
    projectId,
    pendingGeneration?.trackId ?? undefined,
  );

  useEffect(() => {
    const snapshot = status.data;
    if (!pendingGeneration || !snapshot) return;
    if (snapshot.state === "failed") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPendingGeneration((current) =>
        current?.id === pendingGeneration.id
          ? { ...current, state: "failed", error: snapshot.error }
          : current,
      );
    }
    if (snapshot.state === "succeeded") {
      setPendingGeneration(null);
      setBranchFromTrack(null);
      qc.invalidateQueries({ queryKey: qk.revisions(projectId) });
      qc.invalidateQueries({ queryKey: qk.project(projectId) });
      qc.invalidateQueries({ queryKey: qk.projectAssets(projectId) });
      qc.invalidateQueries({ queryKey: qk.library() });
    }
  }, [pendingGeneration, projectId, qc, status.data]);

  const pickCompareA = (trackId: string) => {
    setCompareA((current) => (current === trackId ? null : trackId));
    setCompareB((current) => (current === trackId ? null : current));
  };

  const pickCompareB = (trackId: string) => {
    setCompareB((current) => (current === trackId ? null : trackId));
    setCompareA((current) => (current === trackId ? null : current));
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState
            error={error ?? new Error("Project not found")}
            onRetry={() => refetch()}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="-ml-2 h-7 text-xs text-muted-foreground hover:text-foreground mb-1"
        >
          <Link href="/projects">
            <ChevronLeft className="h-3 w-3 mr-0.5" />
            Projects
          </Link>
        </Button>
        <h1 className="page-title">{data.name}</h1>
        {data.description && (
          <p className="text-sm text-muted-foreground mt-1.5">{data.description}</p>
        )}
        <p className="text-xs text-muted-foreground mt-2 font-mono">
          projects/{data.project_id}/
        </p>
      </div>

      <Tabs defaultValue="studio">
        <TabsList>
          <TabsTrigger value="studio">Studio</TabsTrigger>
          <TabsTrigger value="files">Project Files</TabsTrigger>
        </TabsList>

        <TabsContent value="studio" className="space-y-6 pt-4">
          <GenerateForm
            key={branchFromTrack?.track_id ?? "root"}
            projectId={projectId}
            parentTrack={branchFromTrack}
            onClearBranch={() => setBranchFromTrack(null)}
            onGenerationStart={setPendingGeneration}
            onGenerationSuccess={(id, trackId) => {
              setPendingGeneration((current) =>
                current?.id === id ? { ...current, trackId, state: "running" } : current,
              );
            }}
            onGenerationFailed={(id, errorMessage) => {
              setPendingGeneration((current) =>
                current?.id === id
                  ? { ...current, state: "failed", error: errorMessage }
                  : current,
              );
            }}
          />

          <RevisionTree
            projectId={projectId}
            pendingGeneration={pendingGeneration}
            onDismissPendingGeneration={() => setPendingGeneration(null)}
            onBranch={(track) => setBranchFromTrack(track)}
            onPickCompareA={pickCompareA}
            onPickCompareB={pickCompareB}
            compareA={compareA}
            compareB={compareB}
          />

          <CompareDialog
            projectId={projectId}
            a={compareA}
            b={compareB}
            onClose={() => {
              setCompareA(null);
              setCompareB(null);
            }}
          />
        </TabsContent>

        <TabsContent value="files" className="space-y-4 pt-4">
          <UploadForm projectId={projectId} title="Reference Clips" />
          <ProjectAssetExplorer projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
