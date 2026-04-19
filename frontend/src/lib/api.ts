import type { RunResult } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function uploadVideo(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<{ run_id: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        const msg = (() => {
          try {
            return JSON.parse(xhr.responseText).detail ?? "Upload failed";
          } catch {
            return "Upload failed";
          }
        })();
        reject(new Error(msg));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.open("POST", `${BASE_URL}/upload`);
    xhr.send(form);
  });
}

export async function processRun(
  runId: string,
  runnerHeightM: number = 1.75,
): Promise<{ run_id: string; status: string }> {
  const res = await fetch(`${BASE_URL}/process/${runId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runner_height_m: runnerHeightM }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Process request failed" }));
    throw new Error(err.detail ?? "Process request failed");
  }
  return res.json();
}

export async function getRun(runId: string): Promise<RunResult> {
  const res = await fetch(`${BASE_URL}/run/${runId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Run not found" }));
    throw new Error(err.detail ?? "Run not found");
  }
  return res.json();
}

export function videoUrl(runId: string): string {
  return `${BASE_URL}/video/${runId}`;
}

export function annotatedVideoUrl(runId: string): string {
  return `${BASE_URL}/run/${runId}/annotated-video`;
}
