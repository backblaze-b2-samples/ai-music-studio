"use client";

import Link from "next/link";
import { useState } from "react";
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
import { CompareDialog } from "@/components/revision-tree/compare-dialog";
import { RevisionTree } from "@/components/revision-tree/revision-tree";
import { ProjectAssetExplorer } from "@/components/projects/project-asset-explorer";
import { useProject } from "@/lib/queries";

interface ProjectDetailProps {
  projectId: string;
}

export function ProjectDetail({ projectId }: ProjectDetailProps) {
  const { data, isLoading, error, refetch } = useProject(projectId);
  // Branching seed: when set, the next generation lands as a child of this track.
  const [branchFromTrackId, setBranchFromTrackId] = useState<string | null>(null);
  // Compare seed: a + b
  const [compareA, setCompareA] = useState<string | null>(null);
  const [compareB, setCompareB] = useState<string | null>(null);

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
            projectId={projectId}
            parentTrackId={branchFromTrackId}
            onClearBranch={() => setBranchFromTrackId(null)}
          />

          <RevisionTree
            projectId={projectId}
            onBranch={(trackId) => setBranchFromTrackId(trackId)}
            onPickCompareA={(trackId) => setCompareA(trackId)}
            onPickCompareB={(trackId) => setCompareB(trackId)}
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

        <TabsContent value="files" className="pt-4">
          <ProjectAssetExplorer projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
