"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, ChevronRight, Layers, Activity } from "lucide-react";
import { listRuns, type RunSummary } from "@/lib/api";

function fmt(sec: number | null): string {
  if (!sec) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function relativeTime(ts: number): string {
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function cadenceColor(c: number | null): string {
  if (!c) return "text-zinc-500";
  if (c >= 170 && c <= 185) return "text-emerald-400";
  if (c >= 160) return "text-amber-400";
  return "text-red-400";
}

export default function RecentRuns() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRuns().then((data) => {
      setRuns(data);
      setLoading(false);
    });
  }, []);

  if (loading) return null;
  if (runs.length === 0) return null;

  return (
    <div className="w-full max-w-3xl space-y-4">
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-zinc-600" />
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">
          Recent Runs
        </h2>
      </div>

      <div className="space-y-2">
        {runs.map((run) => (
          <Link
            key={run.run_id}
            href={`/run/${run.run_id}`}
            className="group flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4 transition-all hover:border-zinc-700 hover:bg-zinc-800/60"
          >
            {/* Left: time + duration */}
            <div className="flex items-center gap-4 min-w-0">
              <div className="shrink-0">
                <Activity className="h-4 w-4 text-zinc-600 group-hover:text-emerald-500 transition-colors" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-zinc-200">
                    {fmt(run.duration_sec)} run
                  </span>
                  {run.annotated_video_ready && (
                    <span className="flex items-center gap-1 rounded-full bg-emerald-950/60 border border-emerald-800/40 px-2 py-0.5 text-xs text-emerald-400">
                      <Layers className="h-3 w-3" />
                      annotated
                    </span>
                  )}
                </div>
                <p className="text-xs text-zinc-600 font-mono truncate mt-0.5">
                  {relativeTime(run.created_at)} · {run.run_id.slice(0, 8)}
                </p>
              </div>
            </div>

            {/* Right: key metrics */}
            <div className="flex items-center gap-6 shrink-0">
              <div className="hidden sm:flex flex-col items-end">
                <span className={`text-sm font-semibold tabular-nums ${cadenceColor(run.cadence)}`}>
                  {run.cadence ? `${run.cadence.toFixed(0)} spm` : "—"}
                </span>
                <span className="text-xs text-zinc-600">cadence</span>
              </div>
              <div className="hidden md:flex flex-col items-end">
                <span className="text-sm font-semibold tabular-nums text-zinc-300">
                  {run.symmetry_score ? `${(run.symmetry_score * 100).toFixed(0)}%` : "—"}
                </span>
                <span className="text-xs text-zinc-600">symmetry</span>
              </div>
              <div className="hidden lg:flex flex-col items-end">
                <span className="text-sm font-semibold tabular-nums text-zinc-300">
                  {run.fatigue_time_sec ? fmt(run.fatigue_time_sec) : "none"}
                </span>
                <span className="text-xs text-zinc-600">fatigue</span>
              </div>
              <ChevronRight className="h-4 w-4 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
