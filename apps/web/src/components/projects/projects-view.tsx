"use client";

import { useState } from "react";
import Link from "next/link";
import { Music4, Plus, Trash2 } from "lucide-react";
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
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api-client";
import {
  useCreateProject,
  useDeleteProject,
  useProjects,
} from "@/lib/queries";

export function ProjectsView() {
  const { data, isLoading, error, refetch } = useProjects();
  const create = useCreateProject();
  const remove = useDeleteProject();
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const reset = () => {
    setName("");
    setDescription("");
  };

  const submit = () => {
    if (!name.trim()) {
      toast.error("Project name is required");
      return;
    }
    create.mutate(
      { name: name.trim(), description: description.trim() || null },
      {
        onSuccess: (project) => {
          toast.success(`Created "${project.name}"`);
          setCreateOpen(false);
          reset();
        },
        onError: (err) => {
          const msg = err instanceof ApiError ? err.message : "Failed to create";
          toast.error(msg);
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-36 w-full" />
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

  const projects = data ?? [];

  return (
    <>
      <div className="flex items-center justify-between gap-2 mb-4">
        <span className="text-xs text-muted-foreground">
          {projects.length} {projects.length === 1 ? "project" : "projects"}
        </span>
        <Button size="sm" className="h-8" onClick={() => setCreateOpen(true)}>
          <Plus className="h-3.5 w-3.5 mr-1" />
          New project
        </Button>
      </div>

      {projects.length === 0 ? (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={Music4}
              title="No projects yet"
              description="Create your first project to start generating music."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {projects.map((p) => (
            <Card key={p.project_id} className="hover:shadow-medium transition-shadow">
              <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
                <Link
                  href={`/projects/${p.project_id}`}
                  className="flex-1 min-w-0"
                >
                  <h3 className="card-title truncate">{p.name}</h3>
                  {p.description && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {p.description}
                    </p>
                  )}
                </Link>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-destructive"
                  onClick={() => setConfirmDelete(p.project_id)}
                  aria-label="Delete project"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground flex items-center justify-between">
                <span>
                  {p.track_count} {p.track_count === 1 ? "track" : "tracks"}
                </span>
                {p.archived && (
                  <span className="text-attention font-medium">archived</span>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog
        open={createOpen}
        onOpenChange={(v) => {
          setCreateOpen(v);
          if (!v) reset();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New project</DialogTitle>
            <DialogDescription>
              Projects scope every generated track and its revision history to a
              single B2 prefix.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="project-name">Name</Label>
              <Input
                id="project-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Lo-fi study session"
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="project-description">Description (optional)</Label>
              <Textarea
                id="project-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="A short note about what you're going for."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit} disabled={create.isPending}>
              {create.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={confirmDelete !== null}
        onOpenChange={(v) => !v && setConfirmDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this project?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the project manifest and every track,
              stem, and reference clip under <code className="font-mono">
                projects/{confirmDelete?.slice(0, 8)}…/
              </code>{" "}
              in B2. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={remove.isPending}
              onClick={() => {
                if (!confirmDelete) return;
                remove.mutate(confirmDelete, {
                  onSuccess: (res) => {
                    toast.success(
                      `Deleted ${res.deleted.length} object${
                        res.deleted.length === 1 ? "" : "s"
                      }`,
                    );
                    setConfirmDelete(null);
                  },
                  onError: (err) => {
                    const msg =
                      err instanceof ApiError ? err.message : "Failed to delete";
                    toast.error(msg);
                  },
                });
              }}
            >
              {remove.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
