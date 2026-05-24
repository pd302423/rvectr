"use client";

import { useState, useRef } from "react";

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

export function RecordSubmit({
  exercises,
  submitAction,
}: {
  exercises: ExerciseRow[];
  // Server action — redirects on success so the Promise resolves to never at runtime,
  // but TypeScript sees it as void. Both are assignable to this union.
  submitAction: () => Promise<never> | Promise<void>;
}) {
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [states, setStates] = useState<Record<string, UploadState>>({});
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const uploadedCount = Object.values(files).filter(Boolean).length;

  function handleFileChange(exerciseId: string, file: File | null) {
    setFiles((prev) => ({ ...prev, [exerciseId]: file }));
    setStates((prev) => ({ ...prev, [exerciseId]: file ? "selected" : "idle" }));
  }

  function removeFile(exerciseId: string) {
    setFiles((prev) => ({ ...prev, [exerciseId]: null }));
    setStates((prev) => ({ ...prev, [exerciseId]: "idle" }));
    const inp = inputRefs.current[exerciseId];
    if (inp) inp.value = "";
  }

  return (
    <>
      <div className="space-y-px border border-border rounded overflow-hidden mb-8">
        {exercises.map((ex, i) => {
          const file = files[ex.id];
          const state = states[ex.id] ?? "idle";
          const isSelected = state === "selected" || state === "done";

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
                {isSelected && (
                  <span className="text-[10px] font-mono border border-emerald-200 bg-emerald-50 text-emerald-700 rounded px-2 py-0.5 shrink-0">
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
                onChange={(e) => handleFileChange(ex.id, e.target.files?.[0] ?? null)}
              />

              {/* Upload area */}
              {isSelected && file ? (
                <div className="rounded border border-emerald-200 bg-emerald-50 px-4 py-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-emerald-800 truncate">{file.name}</p>
                    <p className="font-mono text-[10px] text-emerald-600 mt-0.5">
                      {(file.size / (1024 * 1024)).toFixed(1)} MB
                      {file.size > 200 * 1024 * 1024 && (
                        <span className="ml-2 text-amber-600">· large file — may take longer to upload</span>
                      )}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(ex.id)}
                    className="font-mono text-[10px] text-muted-foreground hover:text-foreground transition-colors shrink-0"
                  >
                    replace
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => inputRefs.current[ex.id]?.click()}
                  className="w-full rounded border border-dashed border-border hover:border-foreground/40 bg-background hover:bg-muted/20 px-4 py-4 transition-colors text-center"
                >
                  <span className="font-mono text-xs text-muted-foreground">
                    ↑ tap to select video
                  </span>
                  <span className="block font-mono text-[10px] text-muted-foreground/50 mt-1">
                    .mp4 · .mov — record on your phone, then upload here
                  </span>
                </button>
              )}

            </div>
          );
        })}
      </div>

      {/* Submit section */}
      <div className="rounded border border-border bg-card p-5">
        <div className="flex items-start justify-between gap-4">
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
                You can submit with partial recordings — missing tests will be flagged for a future session.
                For best results, upload all {exercises.length} tests.
              </p>
            )}
            {uploadedCount === exercises.length && (
              <p className="text-xs text-emerald-700 mt-1.5">
                All tests recorded. Vector will grade each rep for form quality.
              </p>
            )}
          </div>
          <form action={submitAction} className="shrink-0">
            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded bg-foreground px-5 py-2.5 font-mono text-sm text-background hover:opacity-90 transition-opacity"
            >
              Submit assessment →
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
