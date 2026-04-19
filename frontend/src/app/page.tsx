"use client";

import { useRouter } from "next/navigation";
import VideoUpload from "@/components/VideoUpload";
import RecentRuns from "@/components/RecentRuns";
import { processRun } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();

  const handleUploadComplete = async (runId: string, heightM: number) => {
    // Trigger background processing then navigate immediately
    processRun(runId, heightM).catch(() => {
      // Errors are surfaced on the run page via polling
    });
    router.push(`/run/${runId}`);
  };

  return (
    <div className="flex flex-col items-center gap-12 py-8">
      {/* Hero */}
      <div className="text-center space-y-4 max-w-2xl">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-100">
          Biomechanical Running Analysis
        </h1>
        <p className="text-lg text-zinc-400 leading-relaxed">
          Upload a running video and receive instant metrics on cadence, stride length,
          vertical oscillation, symmetry, and personalised coaching insights — no wearables
          needed.
        </p>
        <div className="flex flex-wrap justify-center gap-2 text-xs text-zinc-500">
          {[
            "Cadence detection",
            "Stride length",
            "Vertical oscillation",
            "L/R symmetry",
            "Fatigue onset",
            "Overstriding",
          ].map((tag) => (
            <span
              key={tag}
              className="px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Upload card */}
      <div className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-zinc-900/50 p-8">
        <VideoUpload onUploadComplete={handleUploadComplete} />
      </div>

      {/* How it works */}
      <div className="w-full max-w-3xl">
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-6 text-center">
          How it works
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              step: "1",
              title: "Upload",
              desc: "Upload an MP4 video of yourself running — treadmill side-view works best.",
            },
            {
              step: "2",
              title: "Analyse",
              desc: "MediaPipe extracts 33 pose landmarks per frame and our metrics engine processes the data.",
            },
            {
              step: "3",
              title: "Improve",
              desc: "Review your metrics, charts, and personalised coaching insights to run more efficiently.",
            },
          ].map((item) => (
            <div
              key={item.step}
              className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-2"
            >
              <div className="h-7 w-7 rounded-lg bg-emerald-950 border border-emerald-800 text-emerald-400 text-sm font-bold flex items-center justify-center">
                {item.step}
              </div>
              <p className="font-semibold text-zinc-200">{item.title}</p>
              <p className="text-sm text-zinc-500 leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <RecentRuns />
    </div>
  );
}
