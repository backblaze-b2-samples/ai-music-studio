"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  bulkDeleteAudioAssets,
  bulkDeleteFiles,
  createProject,
  deleteAudioAsset,
  deleteFile,
  deleteProject,
  generateTrack,
  getFiles,
  getFileStats,
  getLibrary,
  getPreviewUrl,
  getProject,
  getProjectAssets,
  getProjects,
  getProjectTrack,
  getRevisionTree,
  getTrackDiff,
  getUploadActivity,
} from "@/lib/api-client";
import type {
  AudioAsset,
  FileMetadata,
  GenerationRequestBody,
  Project,
  RevisionNode,
  Track,
  TrackDiff,
} from "@ai-music-studio/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  library: (limit?: number) => [...qk.all, "library", limit ?? 100] as const,
  // Music-studio
  projects: () => [...qk.all, "projects"] as const,
  project: (id: string) => [...qk.all, "project", id] as const,
  projectTrack: (projectId: string, trackId: string) =>
    [...qk.all, "project", projectId, "track", trackId] as const,
  revisions: (projectId: string) =>
    [...qk.all, "project", projectId, "revisions"] as const,
  compare: (projectId: string, a: string, b: string) =>
    [...qk.all, "project", projectId, "compare", a, b] as const,
  projectAssets: (projectId: string) =>
    [...qk.all, "project", projectId, "assets"] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

export function useBulkDeleteFiles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keys: string[]) => bulkDeleteFiles(keys),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Audio Library ---

export function useLibrary(limit = 100) {
  return useQuery<AudioAsset[], ApiError>({
    queryKey: qk.library(limit),
    queryFn: () => getLibrary(limit),
  });
}

export function useDeleteAudioAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => deleteAudioAsset(key),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

export function useBulkDeleteAudioAssets() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keys: string[]) => bulkDeleteAudioAssets(keys),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Music-studio: Projects ---

export function useProjects() {
  return useQuery<Project[], ApiError>({
    queryKey: qk.projects(),
    queryFn: getProjects,
  });
}

export function useProject(id: string | undefined) {
  return useQuery<Project, ApiError>({
    queryKey: qk.project(id ?? ""),
    queryFn: () => getProject(id as string),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string | null }) =>
      createProject(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.projects() });
      qc.invalidateQueries({ queryKey: qk.stats() });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Music-studio: Generation ---

export function useGenerate(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: GenerationRequestBody) => generateTrack(projectId, body),
    onSuccess: () => {
      // The whole revision tree changes on success; cheap to refetch.
      qc.invalidateQueries({ queryKey: qk.revisions(projectId) });
      qc.invalidateQueries({ queryKey: qk.project(projectId) });
      qc.invalidateQueries({ queryKey: qk.projectAssets(projectId) });
      qc.invalidateQueries({ queryKey: qk.projects() });
    },
  });
}

export function useProjectTrack(
  projectId: string,
  trackId: string | undefined,
) {
  return useQuery<Track, ApiError>({
    queryKey: qk.projectTrack(projectId, trackId ?? ""),
    queryFn: () => getProjectTrack(projectId, trackId as string),
    enabled: !!trackId,
  });
}

// --- Music-studio: Revisions / compare ---

export function useRevisionTree(projectId: string | undefined) {
  return useQuery<RevisionNode[], ApiError>({
    queryKey: qk.revisions(projectId ?? ""),
    queryFn: () => getRevisionTree(projectId as string),
    enabled: !!projectId,
  });
}

export function useCompare(
  projectId: string,
  a: string | undefined,
  b: string | undefined,
) {
  const enabled = !!projectId && !!a && !!b && a !== b;
  return useQuery<TrackDiff, ApiError>({
    queryKey: qk.compare(projectId, a ?? "", b ?? ""),
    queryFn: () => getTrackDiff(projectId, a as string, b as string),
    enabled,
  });
}

// --- Music-studio: Project asset explorer (scoped /files) ---

export function useProjectAssets(projectId: string | undefined) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.projectAssets(projectId ?? ""),
    queryFn: () => getProjectAssets(projectId as string),
    enabled: !!projectId,
  });
}
