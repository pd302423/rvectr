"use client";

import { useState, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import { toast } from "sonner";
import { LiveRecorder } from "./live-recorder";

export type ExerciseRow = {
  id: string;
  name: string;
  slug: string;
  order_index: number;
};

type UploadState = "idle" | "selected" | "uploading" | "done";

function getRecordingTip(slug: string): string {
  if (/pull_up|chin_up|muscle_up|ring_row/.test(slug))
    return "Side view · camera at bar height · 2–3 m away";
  if (/plank|hollow/.test(slug))
    return "Side view · camera 10–20 cm above floor · 2–3 m away";
  if (/l_sit|tuck_l/.test(slug))
    return "Side view · camera at hip height · 2 m away";
  if (/squat|pistol|shrimp|lunge/.test(slug))
    return "45° diagonal view · camera at hip height · 3–4 m away";
  return "Side view · camera at shoulder height · 3–4 m away";
}

/**
 * Performs a direct client-side upload to Supabase Storage using XMLHttpRequest.
 * Bypasses Vercel request body limits and supports progress updates.
 */
function uploadFileWithXhr(
  file: File,
  storagePath: string,
  token: string,
  onProgress: (percent: number) => void
): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    
    if (!supabaseUrl) {
      reject(new Error("Supabase URL is not configured."));
      return;
    }
    
    const uploadUrl = `${supabaseUrl}/storage/v1/object/assessment-videos/${storagePath}`;
    
    xhr.open("POST", uploadUrl, true);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.setRequestHeader("apikey", process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
    xhr.setRequestHeader("Content-Type", file.type || "video/mp4");
    xhr.setRequestHeader("x-upsert", "true"); // Allows overwriting existing test videos
    
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    };
    
    xhr.onload = () => {
      if (xhr.status === 200 || xhr.status === 201) {
        resolve(storagePath);
      } else {
        try {
          const res = JSON.parse(xhr.responseText);
          reject(new Error(res.message || `Upload failed with status ${xhr.status}`));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    };
    
    xhr.onerror = () => {
      reject(new Error("Network connection error occurred during upload."));
    };
    
    xhr.send(file);
  });
export function RecordSubmit({
  exercises,
  submitAction,
}: {
  exercises: { id: string; slug: string; name: string; order_index: number }[];
  submitAction: (formData: Record<string, number>) => Promise<void>;
}) {
  const [reps, setReps] = useState<Record<string, number>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const completedCount = Object.keys(reps).length;

  function handleRepChange(exerciseId: string, value: string) {
    const num = parseInt(value, 10);
    if (!isNaN(num) && num >= 0) {
      setReps((prev) => ({ ...prev, [exerciseId]: num }));
    } else if (value === "") {
      setReps((prev) => {
        const copy = { ...prev };
        delete copy[exerciseId];
        return copy;
      });
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isSubmitting) return;

    if (completedCount === 0) {
      toast.error("Please enter reps for at least one exercise.");
      return;
    }

    setIsSubmitting(true);
    try {
      await submitAction(reps);
      toast.success("Assessment results submitted successfully!");
    } catch (err: any) {
      console.error("[RecordSubmit] Submit error:", err);
      toast.error(err.message || "An unexpected error occurred during submission.");
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-px border border-border rounded overflow-hidden mb-8">
        {exercises.map((ex, i) => {
          const val = reps[ex.id] ?? "";
          const isDone = val !== "";

          return (
            <div key={ex.id} className={`bg-card p-5 ${i !== 0 ? "border-t border-border" : ""}`}>

              {/* Exercise header */}
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <span className="font-mono text-[10px] text-muted-foreground/40 uppercase tracking-wider">
                    TEST {String(ex.order_index).padStart(2, "0")}
                  </span>
                  <h3 className="text-sm font-semibold text-foreground mt-0.5">{ex.name}</h3>
                  <p className="font-mono text-[10px] text-muted-foreground mt-1">
                    Input maximum continuous repetitions (or hold time)
                  </p>
                </div>
                {isDone && (
                  <span className="text-[10px] font-mono border border-emerald-200 bg-emerald-50 text-emerald-700 rounded px-2 py-0.5 shrink-0">
                    ✓ logged
                  </span>
                )}
              </div>

              <div className="w-full">
                <input
                  type="number"
                  min="0"
                  disabled={isSubmitting}
                  value={val}
                  onChange={(e) => handleRepChange(ex.id, e.target.value)}
                  placeholder="e.g. 12"
                  className="w-full bg-background border border-border rounded-lg px-4 py-3 font-mono text-lg focus:outline-none focus:ring-1 focus:ring-foreground transition-all disabled:opacity-50"
                />
              </div>

            </div>
          );
        })}
      </div>

      {/* Submit section */}
      <div className="rounded border border-border bg-card p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-1">
              Submission status
            </p>
            <p className="text-sm text-foreground">
              <span className="font-semibold">{completedCount}</span>
              <span className="text-muted-foreground"> / {exercises.length} tests logged</span>
            </p>
            {completedCount < exercises.length && (
              <p className="text-xs text-muted-foreground/70 mt-1.5 leading-relaxed">
                Please enter your reps for at least one test. Missing tests will be flagged for future evaluation.
              </p>
            )}
            {completedCount === exercises.length && (
              <p className="text-xs text-emerald-700 mt-1.5">
                All tests logged. rvector will now build your program.
              </p>
            )}
          </div>
          <div className="shrink-0">
            <button
              type="submit"
              disabled={isSubmitting || completedCount === 0}
              className="inline-flex items-center gap-2 rounded bg-foreground px-5 py-2.5 font-mono text-sm text-background hover:opacity-90 active:opacity-80 transition-all disabled:opacity-50 w-full sm:w-auto justify-center"
            >
              {isSubmitting ? "Submitting..." : "Submit assessment →"}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
