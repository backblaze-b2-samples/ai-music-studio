"use client";

import { useState } from "react";
import { GitBranch, Sparkles, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api-client";
import { useGenerate } from "@/lib/queries";

interface GenerateFormProps {
  projectId: string;
  parentTrackId: string | null;
  onClearBranch: () => void;
}

const STYLES = [
  { value: "ambient", label: "Ambient" },
  { value: "upbeat", label: "Upbeat" },
  { value: "mellow", label: "Mellow / Lo-fi" },
  { value: "cinematic", label: "Cinematic" },
];

export function GenerateForm({
  projectId,
  parentTrackId,
  onClearBranch,
}: GenerateFormProps) {
  const generate = useGenerate(projectId);
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState<string>("ambient");
  const [duration, setDuration] = useState<number>(30);

  const submit = () => {
    if (!prompt.trim()) {
      toast.error("Prompt is required");
      return;
    }
    generate.mutate(
      {
        prompt: prompt.trim(),
        style,
        duration_sec: duration,
        parent_track_id: parentTrackId,
      },
      {
        onSuccess: () => {
          toast.success(
            parentTrackId
              ? "Branched track generated"
              : "Track generated",
          );
          setPrompt("");
          if (parentTrackId) onClearBranch();
        },
        onError: (err) => {
          const msg = err instanceof ApiError ? err.message : "Generation failed";
          toast.error(msg);
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="card-title">
            {parentTrackId ? "Branch from selected track" : "Generate a track"}
          </CardTitle>
          {parentTrackId && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={onClearBranch}
            >
              <X className="h-3 w-3 mr-1" />
              Clear branch
            </Button>
          )}
        </div>
        {parentTrackId && (
          <p className="text-xs text-muted-foreground inline-flex items-center gap-1">
            <GitBranch className="h-3 w-3" />
            parent: <code className="font-mono">{parentTrackId.slice(0, 8)}…</code>
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="prompt">Prompt</Label>
          <Textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="A warm ambient pad with soft bells and a slow tempo."
            rows={3}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="style">Style</Label>
            <Select value={style} onValueChange={setStyle}>
              <SelectTrigger id="style">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STYLES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="duration">Duration (sec)</Label>
            <Input
              id="duration"
              type="number"
              min={5}
              max={300}
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value || "30", 10))}
            />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2">
          <Button onClick={submit} disabled={generate.isPending}>
            <Sparkles className="h-3.5 w-3.5 mr-1" />
            {generate.isPending ? "Generating..." : "Generate"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
