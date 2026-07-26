"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { useBiomechanicsStore, AnalysisResultData } from "@/lib/store";
import { FileVideo, AlertCircle, Loader2, ArrowRight } from "lucide-react";

export default function UploadPage() {
  const router = useRouter();
  const setAnalysis = useBiomechanicsStore((state) => state.setAnalysis);

  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [analysisType, setAnalysisType] = useState("full");
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(10);
    setError(null);

    const formData = new FormData();
    formData.append("video", file);

    try {
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 15;
        });
      }, 300);

      const response = await fetch(
        `/api/v1/analyze?analysis_type=${analysisType}`,
        {
          method: "POST",
          body: formData,
        }
      );

      clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok) {
        // NO MOCK FALLBACK. This previously substituted fabricated joint angles
        // and a posture grade whenever the backend was unreachable, then routed
        // the user to /analysis as though a real analysis had completed. Failing
        // loudly is the only honest behaviour.
        throw new Error(
          `Analysis backend unavailable (HTTP ${response.status}). ` +
            `No analysis was performed. The server-side analysis endpoint has ` +
            `been removed — run the Python pipeline in backend/ directly.`
        );
      }

      const data: AnalysisResultData = await response.json();
      setAnalysis(data);
      router.push("/analysis");
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "An error occurred during video upload"
      );
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight text-foreground font-sans">
            Upload Video Analysis
          </h1>
          <p className="mt-1 text-sm text-muted-foreground font-sans">
            Select an assessment type and upload a movement recording for 3D landmark recovery and telemetry generation.
          </p>
        </div>

        {/* Analysis Type Selector */}
        <div className="mb-8 p-5 rounded-xl border border-border bg-card shadow-xs">
          <label className="block text-xs font-mono uppercase tracking-wider text-muted-foreground mb-3">
            Select Assessment Type
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { id: "full", label: "Full Analysis" },
              { id: "posture", label: "Posture" },
              { id: "gait", label: "Gait Cycle" },
              { id: "range_of_motion", label: "Range of Motion" },
            ].map((type) => (
              <button
                key={type.id}
                type="button"
                onClick={() => setAnalysisType(type.id)}
                className={`py-2.5 px-3 rounded-lg border text-xs font-semibold transition-all ${
                  analysisType === type.id
                    ? "bg-primary text-primary-foreground border-primary shadow-xs"
                    : "bg-secondary/60 text-secondary-foreground border-border hover:bg-secondary"
                }`}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>

        {/* Drop Zone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`p-10 rounded-xl border-2 border-dashed text-center cursor-pointer transition-all ${
            dragActive
              ? "border-primary bg-primary/5"
              : "border-border bg-card hover:border-border/80"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.avi,.mov,.mkv,.webm"
            onChange={handleFileChange}
            className="hidden"
          />
          <div className="p-4 rounded-full bg-secondary text-primary w-fit mx-auto mb-4">
            <FileVideo className="h-8 w-8" />
          </div>
          <p className="text-sm font-semibold text-foreground">
            {file ? file.name : "Drop video file here or click to browse"}
          </p>
          <p className="text-xs text-muted-foreground mt-1 font-mono">
            {file
              ? `${(file.size / (1024 * 1024)).toFixed(2)} MB`
              : "Supports MP4, AVI, MOV, MKV, WebM • Max 100MB"}
          </p>
        </div>

        {/* Action Button */}
        {file && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-6 w-full py-3.5 px-4 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Processing Frame Telemetry... ({progress}%)</span>
              </>
            ) : (
              <>
                <span>Start Biomechanical Analysis</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        )}

        {/* Error Alert */}
        {error && (
          <div className="mt-6 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400 text-xs font-mono flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </main>
    </div>
  );
}
