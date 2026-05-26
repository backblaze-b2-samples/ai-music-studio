"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatDuration } from "@/lib/utils";
import type { FileMetadataDetail } from "@ai-music-studio/shared";

interface FileMetadataPanelProps {
  metadata: FileMetadataDetail;
}

function MetaRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono text-right max-w-[60%] truncate">{value}</span>
    </div>
  );
}

export function FileMetadataPanel({ metadata }: FileMetadataPanelProps) {
  const hasAudioFields =
    metadata.duration_ms !== null ||
    metadata.sample_rate !== null ||
    metadata.channels !== null ||
    metadata.bit_depth !== null ||
    metadata.codec !== null;

  return (
    <Card>
      <CardHeader className="pb-3 px-5 pt-5">
        <CardTitle className="card-title">File Details</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 px-5 pb-5">
        <MetaRow label="Filename" value={metadata.filename} />
        <MetaRow label="Size" value={metadata.size_human} />
        <MetaRow label="Type" value={metadata.mime_type} />
        <MetaRow label="Extension" value={metadata.extension || "none"} />

        <Separator />
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Checksums
        </p>
        <MetaRow label="MD5" value={metadata.md5} />
        <MetaRow label="SHA-256" value={metadata.sha256} />

        {hasAudioFields && (
          <>
            <Separator />
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Audio
            </p>
            {metadata.duration_ms !== null && (
              <MetaRow
                label="Duration"
                value={formatDuration(metadata.duration_ms)}
              />
            )}
            {metadata.sample_rate !== null && (
              <MetaRow
                label="Sample rate"
                value={`${(metadata.sample_rate / 1000).toFixed(1)} kHz`}
              />
            )}
            {metadata.channels !== null && (
              <MetaRow
                label="Channels"
                value={
                  metadata.channels === 1 ? "mono" : `${metadata.channels} ch`
                }
              />
            )}
            {metadata.bit_depth !== null && (
              <MetaRow label="Bit depth" value={`${metadata.bit_depth}-bit`} />
            )}
            {metadata.codec && <MetaRow label="Codec" value={metadata.codec} />}
          </>
        )}

        <Separator />
        <MetaRow
          label="Uploaded"
          value={new Date(metadata.uploaded_at).toLocaleString()}
        />
      </CardContent>
    </Card>
  );
}
