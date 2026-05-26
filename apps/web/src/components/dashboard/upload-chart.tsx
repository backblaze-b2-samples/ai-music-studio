"use client";

import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUploadActivity } from "@/lib/queries";

type ChartMode = "uploads" | "minutes";

export function UploadChart() {
  const { data: activity, error, refetch } = useUploadActivity(7);
  const [mode, setMode] = useState<ChartMode>("uploads");

  // Memoize so recharts doesn't re-render on identical fetches. Bars read
  // from a single `value` field so the chart config stays static and only
  // the label/total flip when the user toggles modes.
  const data = useMemo(
    () =>
      (activity ?? []).map((d) => ({
        date: new Date(d.date + "T00:00:00").toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        value:
          mode === "minutes" ? Math.round(d.duration_ms / 60000) : d.uploads,
      })),
    [activity, mode],
  );

  const total = data.reduce((sum, d) => sum + d.value, 0);
  const totalLabel = mode === "minutes" ? "Minutes" : "Total";
  const activeConfig = useMemo<ChartConfig>(
    () => ({
      value: {
        label: mode === "minutes" ? "Minutes added" : "Audio uploads",
        color: "var(--chart-1)",
      },
    }),
    [mode],
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Upload Activity</CardTitle>
        <CardDescription className="text-xs">Last 7 days</CardDescription>
        <CardAction className="flex items-center gap-3 self-center">
          <Tabs
            value={mode}
            onValueChange={(v) => setMode(v as ChartMode)}
          >
            <TabsList className="h-7 p-0.5">
              <TabsTrigger value="uploads" className="h-6 px-2 text-xs">
                Uploads
              </TabsTrigger>
              <TabsTrigger value="minutes" className="h-6 px-2 text-xs">
                Minutes
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <div className="text-right">
            <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              {totalLabel}
            </div>
            <div className="text-lg font-semibold tabular-nums tracking-tight leading-tight">
              {total}
            </div>
          </div>
        </CardAction>
      </CardHeader>
      <CardContent className="p-5">
        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No activity yet"
            description="Generate a track to see activity trends here."
          />
        ) : (
          <ChartContainer config={activeConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="uploads-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-value)" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="var(--color-value)" stopOpacity={0.55} />
                </linearGradient>
              </defs>
              <CartesianGrid
                vertical={false}
                strokeDasharray="3 3"
                stroke="var(--border)"
              />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tickMargin={10}
                fontSize={11}
              />
              <YAxis
                allowDecimals={false}
                tickLine={false}
                axisLine={false}
                tickMargin={6}
                fontSize={11}
                width={28}
              />
              <ChartTooltip cursor={{ fill: "var(--accent-subtle)" }} content={<ChartTooltipContent />} />
              <Bar
                dataKey="value"
                fill="url(#uploads-fill)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
