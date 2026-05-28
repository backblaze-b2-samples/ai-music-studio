import type {
  AudioAsset,
  DailyUploadCount,
  FileMetadata,
  FileUploadResponse,
  GenerationRequestBody,
  GenerationStatus,
  Project,
  RevisionNode,
  Stem,
  Track,
  TrackDiff,
  UploadStats,
} from "@ai-music-studio/shared";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Typed API error with HTTP status code for caller-side branching. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True for 408, 429, 500, 502, 503, 504 — worth retrying. */
  get isRetryable(): boolean {
    return [408, 429, 500, 502, 503, 504].includes(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    // Network failure (offline, DNS, CORS, etc.)
    throw new ApiError("Network error — check your connection", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail || `API error: ${res.status}`,
      res.status,
    );
  }
  return res.json();
}

export async function getHealth() {
  return apiFetch<{ status: string; b2_connected: boolean }>("/health");
}

export async function getFiles(prefix = "", limit = 100) {
  return apiFetch<FileMetadata[]>(
    `/files?prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );
}

export async function getFileStats() {
  return apiFetch<UploadStats>("/files/stats");
}

export async function getUploadActivity(days = 7) {
  return apiFetch<DailyUploadCount[]>(`/files/stats/activity?days=${days}`);
}

export async function getFile(key: string) {
  return apiFetch<FileMetadata>(`/files/${key}`);
}

export async function getDownloadUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/download`);
}

/** Preview-only presigned URL — does NOT increment the download counter. */
export async function getPreviewUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/preview`);
}

export async function deleteFile(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/files/${key}`, {
    method: "DELETE",
  });
}

export interface BulkDeleteError {
  Key: string;
  Code: string;
  Message: string;
}

export interface BulkDeleteResult {
  deleted: string[];
  errors: BulkDeleteError[];
}

export async function bulkDeleteFiles(keys: string[]) {
  return apiFetch<BulkDeleteResult>("/files/bulk-delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keys }),
  });
}

// --- Audio Library ---

export async function getLibrary(limit = 100) {
  return apiFetch<AudioAsset[]>(`/library?limit=${limit}`);
}

export async function getPlaybackUrl(key: string) {
  return apiFetch<{ url: string; expires_in: number }>(
    `/library/${key}/playback`,
  );
}

export async function getLibraryDownloadUrl(key: string) {
  return apiFetch<{ url: string; expires_in: number }>(
    `/library/${key}/download`,
  );
}

export async function deleteAudioAsset(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/library/${key}`, {
    method: "DELETE",
  });
}

export async function bulkDeleteAudioAssets(keys: string[]) {
  return apiFetch<BulkDeleteResult>("/library/bulk-delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keys }),
  });
}

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void,
  path = "/upload",
): Promise<FileUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new ApiError(body.detail || `Upload failed: ${xhr.status}`, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError("Network error — check your connection", 0)),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError("Upload aborted", 0)),
    );

    xhr.open("POST", `${API_BASE}${path}`);
    xhr.send(formData);
  });
}

export function uploadProjectReference(
  projectId: string,
  file: File,
  onProgress?: (percent: number) => void,
) {
  return uploadFile(file, onProgress, `/projects/${projectId}/reference`);
}

// --- Music-studio: Projects ---

export async function getProjects() {
  return apiFetch<Project[]>("/projects");
}

export async function getProject(projectId: string) {
  return apiFetch<Project>(`/projects/${projectId}`);
}

export async function createProject(body: { name: string; description?: string | null }) {
  return apiFetch<Project>("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteProject(projectId: string) {
  return apiFetch<BulkDeleteResult>(`/projects/${projectId}`, {
    method: "DELETE",
  });
}

// --- Music-studio: Generation ---

export async function generateTrack(
  projectId: string,
  body: GenerationRequestBody,
) {
  return apiFetch<GenerationStatus>(`/projects/${projectId}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getGenerationStatus(projectId: string, trackId: string) {
  return apiFetch<GenerationStatus>(
    `/projects/${projectId}/generations/${trackId}`,
  );
}

export async function getProjectTrack(projectId: string, trackId: string) {
  return apiFetch<Track>(`/projects/${projectId}/tracks/${trackId}`);
}

export async function getTrackPlaybackUrl(projectId: string, trackId: string) {
  return apiFetch<{ url: string; expires_in: number }>(
    `/projects/${projectId}/tracks/${trackId}/playback`,
  );
}

export async function getTrackDownloadUrl(projectId: string, trackId: string) {
  return apiFetch<{ url: string; expires_in: number }>(
    `/projects/${projectId}/tracks/${trackId}/download`,
  );
}

export async function splitTrackStems(projectId: string, trackId: string) {
  return apiFetch<Stem[]>(`/projects/${projectId}/tracks/${trackId}/stems`, {
    method: "POST",
  });
}

// --- Music-studio: Revisions / compare ---

export async function getRevisionTree(projectId: string) {
  return apiFetch<RevisionNode[]>(`/projects/${projectId}/revisions`);
}

export async function getTrackDiff(projectId: string, a: string, b: string) {
  return apiFetch<TrackDiff>(
    `/projects/${projectId}/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`,
  );
}

export async function repairTrackSidecar(projectId: string, trackId: string) {
  return apiFetch<Track>(`/projects/${projectId}/tracks/${trackId}/repair`, {
    method: "POST",
  });
}

// --- Music-studio: Project asset explorer ---

/** Reuse the bucket explorer's /files endpoint, scoped to a project prefix. */
export async function getProjectAssets(projectId: string, limit = 200) {
  return getFiles(`projects/${projectId}/`, limit);
}
