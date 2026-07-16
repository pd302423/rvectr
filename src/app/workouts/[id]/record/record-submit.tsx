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
    xhr.setRequestHeader("Content-Type", file.type);
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
}

export function RecordSubmit({
  exercises,
  submitAction,
}: {
  exercises: ExerciseRow[];
  submitAction: (videoPaths: Record<string, string>) => Promise<never> | Promise<void>;
}) {
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [states, setStates] = useState<Record<string, UploadState>>({});
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [liveRecordingExId, setLiveRecordingExId] = useState<string | null>(null);
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const uploadedCount = Object.values(files).filter(Boolean).length;

  function handleFileChange(exerciseId: string, file: File | null) {
    setFiles((prev) => ({ ...prev, [exerciseId]: file }));
    setStates((prev) => ({ ...prev, [exerciseId]: file ? "selected" : "idle" }));
    if (!file) {
      setUploadProgress((prev) => {
        const copy = { ...prev };
        delete copy[exerciseId];
        return copy;
      });
    }
  }

  function removeFile(exerciseId: string) {
    if (isSubmitting) return;
    setFiles((prev) => ({ ...prev, [exerciseId]: null }));
    setStates((prev) => ({ ...prev, [exerciseId]: "idle" }));
    const inp = inputRefs.current[exerciseId];
    if (inp) inp.value = "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isSubmitting) return;

    // Validate that we have at least one file selected
    if (uploadedCount === 0) {
      toast.error("Please select at least one video to upload.");
      return;
    }

    setIsSubmitting(true);
    const supabase = createClient();
    
    // Get user session to retrieve the access token (JWT)
    const { data: { session }, error: sessionErr } = await supabase.auth.getSession();
    
    if (sessionErr || !session) {
      toast.error("Authentication session not found. Please sign in again.");
      setIsSubmitting(false);
      return;
    }

    const token = session.access_token;
    const userId = session.user.id;
    const uploadedPaths: Record<string, string> = {};

    toast.info("Starting video uploads directly to Supabase Storage...");

    try {
      // Upload files in parallel
      await Promise.all(
        exercises.map(async (ex) => {
          const file = files[ex.id];
          if (!file) return;

          setStates((prev) => ({ ...prev, [ex.id]: "uploading" }));
          
          const fileExt = file.name.split(".").pop() || "mp4";
          // Path in Supabase Storage bucket: userId/workoutExerciseId.extension
          const storagePath = `${userId}/${ex.id}.${fileExt}`;

          try {
            await uploadFileWithXhr(file, storagePath, token, (percent) => {
              setUploadProgress((prev) => ({ ...prev, [ex.id]: percent }));
            });
            
            setStates((prev) => ({ ...prev, [ex.id]: "done" }));
            uploadedPaths[ex.id] = storagePath;
          } catch (uploadErr: any) {
            setStates((prev) => ({ ...prev, [ex.id]: "selected" }));
            throw new Error(`Error uploading "${file.name}": ${uploadErr.message}`);
          }
        })
      );

      toast.success("All videos uploaded successfully! Registering workout results...");
      
      // Call the Next.js Server Action to update Postgres with paths and mark workout completed
      await submitAction(uploadedPaths);
      
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
          const file = files[ex.id];
          const state = states[ex.id] ?? "idle";
          const isSelected = state === "selected" || state === "done";
          const isUploading = state === "uploading";

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
                    {getRecordingTip(ex.slug)}
                  </p>
                </div>
                {state === "done" && (
                  <span className="text-[10px] font-mono border border-emerald-200 bg-emerald-50 text-emerald-700 rounded px-2 py-0.5 shrink-0">
                    ✓ uploaded
                  </span>
                )}
                {state === "selected" && (
                  <span className="text-[10px] font-mono border border-amber-200 bg-amber-50 text-amber-700 rounded px-2 py-0.5 shrink-0">
                    ✓ ready
                  </span>
                )}
              </div>

              {/* Hidden file input */}
              <input
                ref={(el) => { inputRefs.current[ex.id] = el; }}
                type="file"
                accept="video/*,video/mp4,video/quicktime,video/hevc"
                className="hidden"
                disabled={isSubmitting}
                onChange={(e) => handleFileChange(ex.id, e.target.files?.[0] ?? null)}
              />

              {/* Upload area / progress indicator */}
              {isUploading ? (
                <div className="rounded border border-border bg-muted/20 px-4 py-3.5 space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
                    <span>Uploading direct to Supabase...</span>
                    <span className="tabular-nums font-semibold text-foreground">
                      {uploadProgress[ex.id] ?? 0}%
                    </span>
                  </div>
                  <div className="w-full bg-border h-1 overflow-hidden">
                    <div 
                      className="bg-foreground h-full transition-all duration-150"
                      style={{ width: `${uploadProgress[ex.id] ?? 0}%` }}
                    />
                  </div>
                </div>
              ) : isSelected && file ? (
                <div className="rounded border border-emerald-200 bg-emerald-50 px-4 py-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-emerald-800 truncate">{file.name}</p>
                    <p className="font-mono text-[10px] text-emerald-600 mt-0.5">
                      {(file.size / (1024 * 1024)).toFixed(1)} MB
                      {file.size > 100 * 1024 * 1024 && (
                        <span className="ml-2 text-amber-600">· exceeds 100MB limit</span>
                      )}
                    </p>
                  </div>
                  {!isSubmitting && (
                    <button
                      type="button"
                      onClick={() => removeFile(ex.id)}
                      className="font-mono text-[10px] text-muted-foreground hover:text-foreground transition-colors shrink-0"
                    >
                      replace
                    </button>
                  )}
                </div>
              ) : liveRecordingExId === ex.id ? (
                <LiveRecorder
                  onRecordingComplete={(file) => {
                    handleFileChange(ex.id, file);
                    setLiveRecordingExId(null);
                  }}
                  onCancel={() => setLiveRecordingExId(null)}
                />
              ) : (
                <div className="grid grid-cols-2 gap-3 w-full">
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => setLiveRecordingExId(ex.id)}
                    className="flex flex-col items-center justify-center rounded border border-dashed border-border hover:border-foreground/40 bg-background hover:bg-muted/20 px-2 py-4 transition-colors text-center disabled:opacity-50"
                  >
                    <span className="font-mono text-xs text-foreground flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
                      Record live
                    </span>
                    <span className="block font-mono text-[10px] text-muted-foreground mt-1">
                      opens camera
                    </span>
                  </button>
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => inputRefs.current[ex.id]?.click()}
                    className="flex flex-col items-center justify-center rounded border border-dashed border-border hover:border-foreground/40 bg-background hover:bg-muted/20 px-2 py-4 transition-colors text-center disabled:opacity-50"
                  >
                    <span className="font-mono text-xs text-muted-foreground">
                      ↑ Upload video
                    </span>
                    <span className="block font-mono text-[10px] text-muted-foreground/50 mt-1">
                      from gallery
                    </span>
                  </button>
                </div>
              )}

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
              <span className="font-semibold">{uploadedCount}</span>
              <span className="text-muted-foreground"> / {exercises.length} recordings selected</span>
            </p>
            {uploadedCount < exercises.length && (
              <p className="text-xs text-muted-foreground/70 mt-1.5 leading-relaxed">
                Please record and select at least one test video. Missing tests will be flagged for future evaluation.
              </p>
            )}
            {uploadedCount === exercises.length && (
              <p className="text-xs text-emerald-700 mt-1.5">
                All tests recorded. rvector will grade each rep for form quality.
              </p>
            )}
          </div>
          <div className="shrink-0">
            <button
              type="submit"
              disabled={isSubmitting || uploadedCount === 0}
              className="inline-flex items-center gap-2 rounded bg-foreground px-5 py-2.5 font-mono text-sm text-background hover:opacity-90 active:opacity-80 transition-all disabled:opacity-50 w-full sm:w-auto justify-center"
            >
              {isSubmitting ? "Uploading videos..." : "Submit assessment →"}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
