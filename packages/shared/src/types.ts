export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Audio-specific (populated when content_type starts with audio/)
  duration_ms: number | null;
  sample_rate: number | null;
  channels: number | null;
  bit_depth: number | null;
  codec: string | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
  duration_ms: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
  total_audio_assets: number;
  total_duration_ms: number;
  audio_size_bytes: number;
  audio_size_human: string;
  formats: Record<string, number>;
}

/** An audio asset stored in B2. */
export interface AudioAsset {
  key: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  created_at: string;
  duration_ms: number | null;
  sample_rate: number | null;
  channels: number | null;
  bit_depth: number | null;
  codec: string | null;
  title_preview: string | null;
  project_id: string | null;
  track_id: string | null;
  source: "library" | "project";
}

// --- Music-studio types ---

/** A user's music-studio project. */
export interface Project {
  project_id: string;
  name: string;
  description: string | null;
  created_at: string;
  archived: boolean;
  track_count: number;
  owner_id: string | null;
  shared_with: string[];
}

export type StemName = "vocals" | "drums" | "bass" | "other";

/** A stem (vocals/drums/bass/other) — currently stubbed. */
export interface Stem {
  stem_id: string;
  track_id: string;
  name: StemName;
  audio: AudioAsset | null;
}

/** Alternative take from the same generation job. */
export interface TrackVariant {
  variant_id: string;
  track_id: string;
  audio: AudioAsset;
  notes: string | null;
}

/** A generated music track. */
export type GenerationMode = "create" | "new_take" | "extend" | "restyle";

export interface Track {
  track_id: string;
  project_id: string;
  prompt: string;
  style: string | null;
  negative_tags: string | null;
  make_instrumental: boolean;
  generation_mode: GenerationMode;
  continue_at_sec: number | null;
  audio_weight: number | null;
  duration_sec: number;
  provider: string;
  provider_task_id: string | null;
  provider_clip_id: string | null;
  parent_track_id: string | null;
  generation_ms: number | null;
  created_at: string;
  audio: AudioAsset;
  variants: TrackVariant[];
  stems_keys: string[];
  is_orphaned: boolean;
}

export type GenerationStatusName = "queued" | "running" | "succeeded" | "failed";

export interface GenerationStatus {
  track_id: string;
  project_id: string;
  state: GenerationStatusName;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface RevisionNode {
  track: Track;
  children: RevisionNode[];
}

export interface TrackDiff {
  a: Track;
  b: Track;
  prompt_changed: boolean;
  style_changed: boolean;
  negative_tags_changed: boolean;
  instrumental_changed: boolean;
  generation_mode_changed: boolean;
  continue_at_changed: boolean;
  audio_weight_changed: boolean;
  duration_changed: boolean;
  audio_metadata_changed: boolean;
}

export interface GenerationRequestBody {
  prompt: string;
  style?: string | null;
  negative_tags?: string | null;
  make_instrumental?: boolean;
  generation_mode?: GenerationMode;
  continue_at_sec?: number | null;
  audio_weight?: number | null;
  duration_sec?: number;
  parent_track_id?: string | null;
}
