"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, Video, AlertCircle } from "lucide-react";
import clsx from "clsx";

interface Props {
  onUploadComplete: (runId: string, heightM: number) => void;
}

const ACCEPTED = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"];
const MAX_MB = 500;

export default function VideoUpload({ onUploadComplete }: Props) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [height, setHeight] = useState("175");
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (f: File): string | null => {
    if (!ACCEPTED.includes(f.type)) return "Please upload an MP4, MOV, AVI, or WebM video.";
    if (f.size > MAX_MB * 1024 * 1024) return `File exceeds ${MAX_MB} MB limit.`;
    return null;
  };

  const handleFile = (f: File) => {
    const err = validate(f);
    if (err) { setError(err); return; }
    setError(null);
    setFile(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleSubmit = async () => {
    if (!file) return;
    const heightM = parseFloat(height) / 100;
    if (isNaN(heightM) || heightM < 1.0 || heightM > 2.5) {
      setError("Enter a valid height between 100 and 250 cm.");
      return;
    }
    setError(null);

    const { uploadVideo } = await import("@/lib/api");
    try {
      setUploadPct(0);
      const { run_id } = await uploadVideo(file, setUploadPct);
      onUploadComplete(run_id, heightM);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed.");
      setUploadPct(null);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto space-y-6">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          "relative cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-all",
          dragging
            ? "border-emerald-400 bg-emerald-950/30"
            : file
            ? "border-emerald-500 bg-emerald-950/20"
            : "border-zinc-700 bg-zinc-900 hover:border-zinc-500 hover:bg-zinc-800/50",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(",")}
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        <div className="flex flex-col items-center gap-3">
          {file ? (
            <>
              <Video className="h-10 w-10 text-emerald-400" />
              <p className="font-medium text-emerald-300">{file.name}</p>
              <p className="text-sm text-zinc-500">
                {(file.size / 1024 / 1024).toFixed(1)} MB — click to change
              </p>
            </>
          ) : (
            <>
              <Upload className="h-10 w-10 text-zinc-500" />
              <p className="font-semibold text-zinc-300">Drag &amp; drop your running video</p>
              <p className="text-sm text-zinc-500">MP4, MOV, AVI or WebM · up to {MAX_MB} MB</p>
            </>
          )}
        </div>
      </div>

      {/* Height input */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-zinc-400 whitespace-nowrap">
          Runner height
        </label>
        <input
          type="number"
          min={100}
          max={250}
          value={height}
          onChange={(e) => setHeight(e.target.value)}
          className="w-24 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:border-emerald-500 focus:outline-none"
        />
        <span className="text-sm text-zinc-500">cm</span>
        <p className="ml-auto text-xs text-zinc-600">Used to estimate stride length</p>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Upload progress */}
      {uploadPct !== null && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-zinc-500">
            <span>Uploading…</span>
            <span>{uploadPct}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-zinc-800">
            <div
              className="h-1.5 rounded-full bg-emerald-500 transition-all"
              style={{ width: `${uploadPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!file || uploadPct !== null}
        className={clsx(
          "w-full rounded-xl py-3 font-semibold text-sm transition-all",
          file && uploadPct === null
            ? "bg-emerald-600 text-white hover:bg-emerald-500"
            : "cursor-not-allowed bg-zinc-800 text-zinc-500",
        )}
      >
        {uploadPct !== null ? "Uploading…" : "Analyse Run"}
      </button>
    </div>
  );
}
