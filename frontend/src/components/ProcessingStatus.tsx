"use client";

import { useEffect, useRef } from "react";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import type { RunStatus } from "@/lib/types";

interface Props {
  status: RunStatus;
  error?: string | null;
}

const MESSAGES: Record<RunStatus, string> = {
  pending: "Queued for processing…",
  processing: "Extracting pose landmarks and computing metrics…",
  completed: "Analysis complete",
  failed: "Analysis failed",
};

export default function ProcessingStatus({ status, error }: Props) {
  return (
    <div className="flex flex-col items-center gap-6 py-12">
      {status === "completed" ? (
        <CheckCircle2 className="h-14 w-14 text-emerald-400" />
      ) : status === "failed" ? (
        <XCircle className="h-14 w-14 text-red-400" />
      ) : (
        <Loader2 className="h-14 w-14 animate-spin text-emerald-500" />
      )}

      <div className="text-center space-y-2">
        <p className="text-lg font-semibold text-zinc-100">{MESSAGES[status]}</p>
        {(status === "pending" || status === "processing") && (
          <p className="text-sm text-zinc-500">
            This may take a minute depending on video length.
          </p>
        )}
        {error && (
          <p className="text-sm text-red-400 max-w-sm mx-auto">{error}</p>
        )}
      </div>

      {/* Animated steps */}
      {(status === "pending" || status === "processing") && (
        <div className="space-y-2 text-sm text-zinc-500 text-left">
          {["Extracting pose landmarks", "Computing biomechanical metrics", "Running fatigue analysis", "Generating coaching insights"].map(
            (step, i) => (
              <div key={step} className="flex items-center gap-2">
                <div
                  className={`h-1.5 w-1.5 rounded-full ${
                    status === "processing" && i === 1
                      ? "bg-emerald-400 animate-pulse"
                      : "bg-zinc-700"
                  }`}
                />
                {step}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
