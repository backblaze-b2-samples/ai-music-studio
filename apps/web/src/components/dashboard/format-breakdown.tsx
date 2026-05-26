"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFileStats } from "@/lib/queries";

/**
 * Compact breakdown of how many audio assets exist per file format
 * (e.g. `wav 5 · mp3 12 · flac 1`). Sorted by count desc.
 *
 * Returns `null` when the bucket has no audio yet — we don't want to render
 * an empty card on first load. Consumes the same `useFileStats()` query as
 * `StatsCards`; TanStack Query dedupes on the shared `qk.stats()` key.
 */
export function FormatBreakdown() {
  const { data: stats } = useFileStats();
  const formats = stats?.formats ?? {};
  const entries = Object.entries(formats).sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) {
    return null;
  }

  return (
    <Card className="card-hover">
      <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
        <CardTitle className="text-xs font-semibold text-muted-foreground">
          Formats
        </CardTitle>
      </CardHeader>
      <CardContent className="pb-4 px-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          {entries.map(([format, count], i) => (
            <span key={format} className="flex items-center gap-3">
              <span>
                <span className="font-medium">{format}</span>{" "}
                <span className="text-muted-foreground">{count}</span>
              </span>
              {i < entries.length - 1 && (
                <span className="text-muted-foreground/50" aria-hidden>
                  ·
                </span>
              )}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
