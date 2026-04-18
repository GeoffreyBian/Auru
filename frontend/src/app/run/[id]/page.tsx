"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { getRun, videoUrl } from "@/lib/api";
import type { RunResult } from "@/lib/types";
import MetricCard from "@/components/MetricCard";
import RunChart from "@/components/RunChart";
import InsightCard from "@/components/InsightCard";
import VideoPlayer from "@/components/VideoPlayer";
import ProcessingStatus from "@/components/ProcessingStatus";

const POLL_INTERVAL_MS = 3000;

function formatTime(sec: number | null): string {
  if (sec === null || sec === undefined) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function cadenceStatus(c: number): "good" | "warn" | "bad" | "neutral" {
  if (c === 0) return "neutral";
  if (c >= 170 && c <= 185) return "good";
  if (c >= 160) return "warn";
  return "bad";
}

function symmetryStatus(s: number): "good" | "warn" | "bad" | "neutral" {
  if (s >= 0.95) return "good";
  if (s >= 0.85) return "warn";
  return "bad";
}

function voStatus(v: number): "good" | "warn" | "bad" | "neutral" {
  if (v === 0) return "neutral";
  if (v <= 0.035) return "good";
  if (v <= 0.05) return "warn";
  return "bad";
}

export default function RunPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const [result, setResult] = useState<RunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRun = async () => {
    try {
      const data = await getRun(runId);
      setResult(data);
      if (data.status === "completed" || data.status === "failed") {
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load run.");
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
  };

  useEffect(() => {
    fetchRun();
    intervalRef.current = setInterval(fetchRun, POLL_INTERVAL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [runId]);

  if (error) {
    return (
      <div className="text-center py-20 space-y-4">
        <p className="text-red-400">{error}</p>
        <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-300 underline">
          ← Back to upload
        </Link>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex justify-center py-20">
        <RefreshCw className="h-6 w-6 animate-spin text-zinc-600" />
      </div>
    );
  }

  const isProcessing = result.status === "pending" || result.status === "processing";
  const isFailed = result.status === "failed";
  const m = result.metrics;

  // Build fatigue reference lines for cadence chart
  const fatigueRef =
    m?.fatigue_time_sec != null
      ? [{ x: m.fatigue_time_sec, label: "Fatigue", color: "#f97316" }]
      : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          New analysis
        </Link>
        <p className="text-xs text-zinc-600 font-mono">{runId}</p>
      </div>

      {/* Processing / failed state */}
      {(isProcessing || isFailed) && (
        <ProcessingStatus status={result.status} error={result.error} />
      )}

      {/* Completed */}
      {result.status === "completed" && m && (
        <>
          {/* Metric cards */}
          <div>
            <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
              Metrics
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <MetricCard
                label="Cadence"
                value={m.cadence.toFixed(0)}
                unit="spm"
                status={cadenceStatus(m.cadence)}
                description="Steps per minute"
              />
              <MetricCard
                label="Stride Length"
                value={m.stride_length.toFixed(2)}
                unit="m"
                status="neutral"
                description="Approximate"
              />
              <MetricCard
                label="Vert. Oscillation"
                value={(m.vertical_oscillation * 1000).toFixed(1)}
                unit="mm"
                status={voStatus(m.vertical_oscillation)}
                description="Hip bounce (norm.)"
              />
              <MetricCard
                label="Symmetry"
                value={(m.symmetry_score * 100).toFixed(0)}
                unit="%"
                status={symmetryStatus(m.symmetry_score)}
                description="L/R balance"
              />
              <MetricCard
                label="Fatigue Onset"
                value={formatTime(m.fatigue_time_sec)}
                status={m.fatigue_time_sec !== null ? "warn" : "good"}
                description={m.fatigue_time_sec !== null ? "Time into run" : "Not detected"}
              />
              <MetricCard
                label="Overstriding"
                value={m.overstriding_count}
                unit="events"
                status={m.overstriding_count > 5 ? "warn" : m.overstriding_count > 0 ? "neutral" : "good"}
                description="Detected contacts"
              />
            </div>
          </div>

          {/* Two-column layout: video + insights */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">
                Video
              </h2>
              <VideoPlayer src={videoUrl(runId)} />
              {/* Video metadata */}
              {result.metadata?.duration_sec && (
                <div className="flex gap-4 text-xs text-zinc-600">
                  <span>{formatTime(result.metadata.duration_sec)} duration</span>
                  <span>{result.metadata.fps?.toFixed(0)} fps</span>
                  <span>{result.metadata.width}×{result.metadata.height}</span>
                </div>
              )}
            </div>
            <div className="space-y-4">
              <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">
                Coaching
              </h2>
              <InsightCard insights={result.insights} />
            </div>
          </div>

          {/* Charts */}
          <div>
            <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
              Charts
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <RunChart
                title="Cadence over time"
                data={result.cadence_over_time}
                color="#10b981"
                unit=" spm"
                referenceLines={fatigueRef}
                formatValue={(v) => v.toFixed(0)}
                yDomain={[100, 220]}
              />
              <RunChart
                title="Hip vertical movement"
                data={result.hip_y_over_time}
                color="#6366f1"
                invertY
                formatValue={(v) => v.toFixed(3)}
              />
              <RunChart
                title="Left ankle — foot strikes"
                data={result.left_ankle_y_over_time}
                color="#f59e0b"
                invertY
                formatValue={(v) => v.toFixed(3)}
              />
              <RunChart
                title="Right ankle — foot strikes"
                data={result.right_ankle_y_over_time}
                color="#ec4899"
                invertY
                formatValue={(v) => v.toFixed(3)}
              />
            </div>
          </div>

          {/* Events timeline */}
          {m.events.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
                Events
              </h2>
              <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="text-left px-5 py-3 text-zinc-500 font-medium">Type</th>
                      <th className="text-left px-5 py-3 text-zinc-500 font-medium">Time</th>
                      <th className="text-left px-5 py-3 text-zinc-500 font-medium">Frame</th>
                    </tr>
                  </thead>
                  <tbody>
                    {m.events.map((evt, i) => (
                      <tr key={i} className="border-b border-zinc-800/50 last:border-0">
                        <td className="px-5 py-3">
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                              evt.type === "fatigue"
                                ? "bg-orange-950/50 text-orange-400"
                                : "bg-red-950/50 text-red-400"
                            }`}
                          >
                            {evt.type}
                          </span>
                        </td>
                        <td className="px-5 py-3 tabular-nums text-zinc-300">
                          {formatTime(evt.time_sec)}
                        </td>
                        <td className="px-5 py-3 tabular-nums text-zinc-500">{evt.frame}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
