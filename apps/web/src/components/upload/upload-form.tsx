"use client";

import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { FileRejection } from "react-dropzone";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dropzone } from "./dropzone";
import { UploadProgress, type UploadItem } from "./upload-progress";
import { uploadFile, uploadProjectReference } from "@/lib/api-client";
import { humanizeBytes } from "@/lib/utils";
import { qk } from "@/lib/queries";

interface UploadFormProps {
  projectId?: string;
  title?: string;
}

export function UploadForm({ projectId, title = "Upload Audio" }: UploadFormProps) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const qc = useQueryClient();

  const handleFilesRejected = useCallback((rejections: FileRejection[]) => {
    for (const rejection of rejections) {
      const name = rejection.file.name;
      const errors = rejection.errors.map((e) => {
        if (e.code === "file-too-large") {
          return `exceeds 100MB limit (${humanizeBytes(rejection.file.size)})`;
        }
        return e.message;
      });
      toast.error(`${name}: ${errors.join(", ")}`);
    }
  }, []);

  const handleFilesSelected = useCallback((files: File[]) => {
    const newItems: UploadItem[] = files.map((file) => ({
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      file,
      progress: 0,
      status: "uploading" as const,
    }));
    setItems((prev) => [...prev, ...newItems]);
    setUploading(true);

    const uploadQueue = async () => {
      let anySuccess = false;
      for (const item of newItems) {
        try {
          const onProgress = (percent: number) => {
            setItems((prev) =>
              prev.map((i) =>
                i.id === item.id ? { ...i, progress: percent } : i
              )
            );
          };
          if (projectId) {
            await uploadProjectReference(projectId, item.file, onProgress);
          } else {
            await uploadFile(item.file, onProgress);
          }
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? { ...i, status: "complete", progress: 100 }
                : i
            )
          );
          toast.success(`${item.file.name} uploaded successfully`);
          anySuccess = true;
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Upload failed";
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? { ...i, status: "error", error: message }
                : i
            )
          );
          toast.error(`Failed to upload ${item.file.name}: ${message}`);
        }
      }
      setUploading(false);
      if (anySuccess) {
        qc.invalidateQueries({ queryKey: qk.all });
      }
    };

    uploadQueue().catch(console.error);
  }, [projectId, qc]);

  const clearCompleted = useCallback(() => {
    setItems((prev) => prev.filter((i) => i.status === "uploading"));
  }, []);

  const hasCompleted = items.some(
    (i) => i.status === "complete" || i.status === "error"
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-5 space-y-4">
        <Dropzone
          onFilesSelected={handleFilesSelected}
          onFilesRejected={handleFilesRejected}
          disabled={uploading}
        />
        <UploadProgress items={items} />
        {hasCompleted && !uploading && (
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={clearCompleted}>
              Clear completed
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
