"use client";

import { AlertCircle, GitBranch, Repeat, Sparkles, Wand2, X } from "lucide-react";

import type { PendingGeneration } from "@/components/generation/pending-generation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { GeneratingLoader } from "@/components/ui/generating-loader";
import { cn } from "@/lib/utils";

interface PendingTrackNodeProps {
  pending: PendingGeneration;
  onDismiss: () => void;
}

function modeLabel(mode: PendingGeneration["generationMode"]): string {
  if (mode === "extend") return "extend";
  if (mode === "restyle") return "restyle";
  if (mode === "new_take") return "new take";
  return "create";
}

function modeIcon(mode: PendingGeneration["generationMode"]) {
  if (mode === "extend") return <Repeat className="h-2.5 w-2.5 mr-0.5" />;
  if (mode === "restyle") return <Wand2 className="h-2.5 w-2.5 mr-0.5" />;
  return <Sparkles className="h-2.5 w-2.5 mr-0.5" />;
}

export function PendingTrackNode({ pending, onDismiss }: PendingTrackNodeProps) {
  const isFailed = pending.state === "failed";

  return (
    <Card
      className={cn(
        "border-dashed",
        isFailed
          ? "border-destructive/50 bg-destructive/5"
          : "border-primary/40 bg-primary/[0.03]",
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="shrink-0">
            {isFailed ? (
              <div className="flex h-12 w-12 items-center justify-center rounded-full border border-destructive/30 text-destructive">
                <AlertCircle className="h-5 w-5" />
              </div>
            ) : (
              <GeneratingLoader size="md" variant="stars" label="Creating" />
            )}
          </div>

          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge variant={isFailed ? "destructive" : "default"} className="h-4 px-1.5 text-[10px]">
                {isFailed ? "failed" : "generating"}
              </Badge>
              <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">
                {modeIcon(pending.generationMode)}
                {modeLabel(pending.generationMode)}
              </Badge>
              {pending.parentTrackId && (
                <Badge variant="outline" className="h-4 px-1.5 text-[10px]">
                  <GitBranch className="h-2.5 w-2.5 mr-0.5" />
                  {pending.parentTrackId.slice(0, 8)}...
                </Badge>
              )}
              {pending.makeInstrumental && (
                <Badge variant="outline" className="h-4 px-1.5 text-[10px]">
                  instrumental
                </Badge>
              )}
            </div>

            <div>
              <p className="text-sm font-medium line-clamp-2">{pending.prompt}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {pending.style || "No style"} · waiting on provider
              </p>
              {pending.negativeTags && (
                <p className="text-[11px] text-muted-foreground mt-1 line-clamp-1">
                  Avoid: {pending.negativeTags}
                </p>
              )}
              {pending.generationMode === "extend" && (
                <p className="text-[11px] text-muted-foreground mt-1">
                  Extend from: {pending.continueAtSec ?? 0}s
                </p>
              )}
              {pending.generationMode === "restyle" && (
                <p className="text-[11px] text-muted-foreground mt-1">
                  Source influence: {pending.audioWeight ?? 0.6}
                </p>
              )}
              {isFailed && pending.error && (
                <p className="text-xs text-destructive mt-2">{pending.error}</p>
              )}
            </div>
          </div>

          {isFailed && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 shrink-0"
              title="Dismiss failed generation"
              onClick={onDismiss}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
