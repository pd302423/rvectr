import { redirect, notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSkill } from "@/lib/calisthenics";
import { completeWorkout, skipWorkout } from "@/app/workouts/actions";

// ─── Types ────────────────────────────────────────────────────────────────────

type WorkoutExercise = {
  id: string;
  exercise_slug: string;
  order_index: number;
  intent: string;
  target_sets: number;
  target_reps_min: number;
  target_reps_max: number;
  rest_seconds_min: number;
  rest_seconds_max: number;
  tempo: string | null;
  biomechanical_note: string | null;
  progression_context: string | null;
};

// ─── Recording guide helper ───────────────────────────────────────────────────

type RecordingGuide = {
  angle: string;
  cameraHeight: string;
  distance: string;
  framing: string;
  takes: number;
  tip: string;
};

function getRecordingGuide(slug: string): RecordingGuide {
  if (/pull_up|chin_up|muscle_up|front_lever|dead_hang|ring_row|archer_pull/.test(slug)) {
    return {
      angle: "Strict side view",
      cameraHeight: "At bar height — camera level with the bar",
      distance: "2–3 m from the side",
      framing: "Full body from feet to top of head — dead hang start and chin-above-bar clearance must both be visible",
      takes: 2,
      tip: "Rest phone on a shelf or lean against a bag. The full descent to dead hang AND chin above bar must be in frame the entire time.",
    };
  }
  if (/handstand|planche/.test(slug)) {
    return {
      angle: "Strict side view",
      cameraHeight: "Hip height when standing (approx. 80–100 cm) — at mid-body when inverted",
      distance: "3–4 m from the side",
      framing: "Full body from wrists to pointed toes — entire body line must be visible",
      takes: 2,
      tip: "Use a wall as background reference — straight body line vs banana curve is the primary CV metric. Record before entering the position.",
    };
  }
  if (/l_sit|tuck_l/.test(slug)) {
    return {
      angle: "Strict side view",
      cameraHeight: "Hip height (approx. 60–80 cm off ground)",
      distance: "2 m from the side",
      framing: "Hips, arms, and legs must all be visible — leg angle relative to horizontal is the key graded metric",
      takes: 2,
      tip: "Lean phone against a wall. The CV model checks hip position relative to hands, leg angle from horizontal, and shoulder depression.",
    };
  }
  if (/plank|hollow/.test(slug)) {
    return {
      angle: "Strict side view",
      cameraHeight: "10–20 cm above the floor — prop phone on a water bottle",
      distance: "2–3 m from the side",
      framing: "Full body from ankles to head — lower back contact with the floor must be clearly visible",
      takes: 2,
      tip: "For hollow hold: the camera must clearly see whether your lower back peels off the floor — that is the failure point the CV model watches for.",
    };
  }
  if (/squat|lunge|pistol|shrimp|bridge|nordic/.test(slug)) {
    return {
      angle: "45° diagonal — halfway between strict side and front view",
      cameraHeight: "Hip height (approx. 80–100 cm)",
      distance: "3–4 m away",
      framing: "Full body — knee tracking over toes and hip crease depth must both be visible",
      takes: 3,
      tip: "The diagonal captures sagittal plane depth AND frontal plane knee-valgus simultaneously. Stand phone against a wall at the 45° position.",
    };
  }
  // Default: push movements
  return {
    angle: "Strict side view",
    cameraHeight: "Shoulder height when at the bottom position (approx. 40–60 cm)",
    distance: "3–4 m from the side",
    framing: "Full body from ankles to top of head — chest-to-floor depth and elbow angle at bottom must be visible",
    takes: 2,
    tip: "Prop phone against a wall or bag at shoulder height. Record the entire set without stopping the camera between reps.",
  };
}

// ─── Other helpers ────────────────────────────────────────────────────────────

// Left-border accent per protocol — colour-codes the card at a glance
const PROTOCOL_ACCENTS: Record<string, string> = {
  max_effort: "border-l-[3px] border-l-red-400",
  timed_hold: "border-l-[3px] border-l-violet-400",
  graded:     "border-l-[3px] border-l-amber-400",
};

const PROTOCOL_LABELS: Record<string, { label: string; cls: string; description: string }> = {
  max_effort: {
    label: "Max effort",
    cls: "border-red-200 bg-red-50 text-red-800",
    description: "Perform reps to volitional failure. Stop the moment form breaks — not when tired.",
  },
  timed_hold: {
    label: "Timed hold",
    cls: "border-violet-200 bg-violet-50 text-violet-800",
    description: "Hold position until form failure. The moment the stated failure criterion occurs, the test ends.",
  },
  graded: {
    label: "Form graded",
    cls: "border-amber-200 bg-amber-50 text-amber-800",
    description: "Fixed reps — quality of every rep is what is being scored, not quantity. Execute deliberately.",
  },
};

const INTENT_STYLES: Record<string, { label: string; cls: string }> = {
  strength:          { label: "Strength",        cls: "border-emerald-300 bg-emerald-50 text-emerald-800" },
  hypertrophy:       { label: "Hypertrophy",     cls: "border-blue-200 bg-blue-50 text-blue-800" },
  skill_acquisition: { label: "Skill",           cls: "border-amber-200 bg-amber-50 text-amber-800" },
  tendon_prep:       { label: "Tendon Prep",     cls: "border-violet-200 bg-violet-50 text-violet-800" },
  active_recovery:   { label: "Active Recovery", cls: "border-border bg-muted/40 text-muted-foreground" },
};

function formatIndex(n: number): string {
  return String(n).padStart(2, "0");
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function WorkoutPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");

  const { data: workout } = await supabase
    .from("workouts")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!workout) notFound();

  const { data: exercises } = await supabase
    .from("workout_exercises")
    .select("*")
    .eq("workout_id", id)
    .order("order_index", { ascending: true });

  const rows: WorkoutExercise[] = exercises ?? [];
  const isAssessment = workout.session_focus === "assessment";
  const isCompleted = workout.status === "completed";
  const isSkipped = workout.status === "skipped";

  const completeAction = completeWorkout.bind(null, workout.id);
  const skipAction = skipWorkout.bind(null, workout.id);

  return (
    <main className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-3xl">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <header className="mb-10 border-b border-border pb-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
                {isAssessment ? "§ Strength assessment protocol" : "§ Session report"}
              </p>
              <h1
                style={{ fontFamily: "var(--font-serif)" }}
                className="mt-3 text-4xl leading-tight tracking-tight"
              >
                {isAssessment ? "Baseline Assessment" : (
                  workout.session_focus.charAt(0).toUpperCase() + workout.session_focus.slice(1) + " Session"
                )}
              </h1>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {isAssessment ? (
                  <span className="text-xs border border-sky-200 bg-sky-50 text-sky-700 rounded px-2 py-0.5">
                    diagnostic · not a training session
                  </span>
                ) : (
                  <>
                    <span className="text-xs border border-border rounded px-2 py-0.5 text-muted-foreground">
                      {workout.block}
                    </span>
                    <span className="text-xs border border-border rounded px-2 py-0.5 text-muted-foreground">
                      Week {workout.week_number}
                    </span>
                  </>
                )}
                {isCompleted && (
                  <span className="text-xs border border-emerald-300 bg-emerald-50 rounded px-2 py-0.5 text-emerald-700">
                    ✓ completed
                  </span>
                )}
                {isSkipped && (
                  <span className="text-xs border border-border rounded px-2 py-0.5 text-muted-foreground/60">
                    skipped
                  </span>
                )}
              </div>
            </div>
            <a
              href="/dashboard"
              className="font-mono text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors shrink-0 -mr-2 px-2 py-2"
            >
              ← dashboard
            </a>
          </div>
        </header>

        {/* ── Assessment prep banner ─────────────────────────────────────── */}
        {isAssessment && (
          <div className="mb-8 grid grid-cols-3 gap-px bg-border border border-border rounded overflow-hidden text-center">
            <div className="bg-card py-4 px-2">
              <p className="font-mono text-lg tabular-nums text-foreground">{rows.length}</p>
              <p className="font-mono text-[10px] text-muted-foreground mt-0.5">tests</p>
            </div>
            <div className="bg-card py-4 px-2">
              <p className="font-mono text-lg tabular-nums text-foreground">5 min</p>
              <p className="font-mono text-[10px] text-muted-foreground mt-0.5">rest between each</p>
            </div>
            <div className="bg-card py-4 px-2">
              <p className="font-mono text-lg tabular-nums text-foreground">10 min</p>
              <p className="font-mono text-[10px] text-muted-foreground mt-0.5">warm-up first</p>
            </div>
          </div>
        )}

        {/* ── Coach rationale (training sessions only) ────────────────────── */}
        {!isAssessment && workout.ai_rationale && (
          <div className="mb-8 rounded border border-border bg-card p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">
              Coach rationale
            </p>
            <p className="text-sm text-foreground leading-relaxed">
              {workout.ai_rationale}
            </p>
          </div>
        )}

        {/* ── Exercises / Tests ───────────────────────────────────────────── */}
        <div className="space-y-px border border-border rounded overflow-hidden">
          {rows.map((ex, i) => {
            const skill = getSkill(ex.exercise_slug);
            const name = skill?.label ?? ex.exercise_slug.replace(/_/g, " ");
            const intent = INTENT_STYLES[ex.intent] ?? {
              label: ex.intent,
              cls: "border-border bg-muted/40 text-muted-foreground",
            };

            const protocol = ex.tempo ? PROTOCOL_LABELS[ex.tempo] : null;
            const accent = isAssessment ? (PROTOCOL_ACCENTS[ex.tempo ?? ""] ?? "") : "";
            const guide = getRecordingGuide(ex.exercise_slug);

            return (
              <div key={ex.id} className={`bg-card p-5 ${i !== 0 ? "border-t border-border" : ""} ${accent}`}>

                {/* ── Header row ── */}
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="flex items-baseline gap-3">
                    <span className="font-mono text-xs text-muted-foreground/60 tabular-nums shrink-0">
                      {isAssessment ? `TEST ${formatIndex(ex.order_index)}` : formatIndex(ex.order_index)}
                    </span>
                    <h2 className="text-base font-semibold text-foreground leading-snug">
                      {name}
                    </h2>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {isAssessment && protocol && (
                      <span className={`font-mono text-[10px] uppercase tracking-wider border rounded px-2 py-0.5 ${protocol.cls}`}>
                        {protocol.label}
                      </span>
                    )}
                    {!isAssessment && (
                      <span className={`font-mono text-[10px] uppercase tracking-wider border rounded px-2 py-0.5 ${intent.cls}`}>
                        {intent.label}
                      </span>
                    )}
                  </div>
                </div>

                {/* ── Non-assessment prescription ── */}
                {!isAssessment && (
                  <div className="flex flex-wrap gap-4 mb-4">
                    <div>
                      <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground mb-0.5">Prescription</p>
                      <p className="font-mono text-sm font-semibold text-foreground tabular-nums">
                        {ex.target_sets} × {ex.target_reps_min}–{ex.target_reps_max} reps
                      </p>
                    </div>
                    <div>
                      <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground mb-0.5">Rest</p>
                      <p className="font-mono text-sm text-foreground tabular-nums">
                        {Math.round(ex.rest_seconds_min / 60)}–{Math.round(ex.rest_seconds_max / 60)} min
                      </p>
                    </div>
                    {ex.tempo && !["max_effort", "timed_hold", "graded"].includes(ex.tempo) && (
                      <div>
                        <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground mb-0.5">Tempo</p>
                        <p className="font-mono text-sm text-foreground">{ex.tempo}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* ── Biomechanical note (training sessions only) ── */}
                {!isAssessment && ex.biomechanical_note && (
                  <div className="mb-4">
                    <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground mb-1.5">
                      Biomechanical note
                    </p>
                    <p className="text-xs text-foreground leading-relaxed">
                      {ex.biomechanical_note}
                    </p>
                  </div>
                )}

                {/* ── Progression context (training sessions only) ── */}
                {!isAssessment && ex.progression_context && (
                  <div className="mb-4 border-t border-border pt-3 mt-3">
                    <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground mb-1.5">
                      Progression context
                    </p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {ex.progression_context}
                    </p>
                  </div>
                )}

                {/* ── Recording setup (assessment only) ── */}
                {isAssessment && (
                  <div className="border-t border-border pt-4 mt-1">
                    <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground mb-2">
                      Recording setup
                    </p>
                    <div className="rounded border border-border bg-background overflow-hidden">

                      {/* Takes + angle — primary info row */}
                      <div className="flex items-center gap-3.5 px-4 py-3">
                        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-foreground font-mono text-xs font-semibold text-background shrink-0">
                          {guide.takes}×
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground leading-tight">{guide.angle}</p>
                          <p className="font-mono text-[10px] text-muted-foreground mt-0.5">
                            {guide.cameraHeight} · {guide.distance}
                          </p>
                        </div>
                      </div>

                      {/* Framing */}
                      <div className="border-t border-border px-4 py-3">
                        <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground mb-1">
                          Framing
                        </p>
                        <p className="text-xs text-foreground leading-relaxed">{guide.framing}</p>
                      </div>

                      {/* Tip — muted background to visually separate */}
                      <div className="border-t border-border bg-muted/40 px-4 py-3">
                        <p className="text-xs text-muted-foreground leading-relaxed">{guide.tip}</p>
                      </div>

                    </div>
                  </div>
                )}

                {/* ── Rest reminder ── */}
                {isAssessment && i < rows.length - 1 && (
                  <div className="mt-4 border-t border-border pt-3">
                    <p className="font-mono text-[9px] text-muted-foreground/50 uppercase tracking-wider">
                      ↓ Rest 5 full minutes before the next test
                    </p>
                  </div>
                )}

              </div>
            );
          })}

          {rows.length === 0 && (
            <div className="bg-card p-8 text-center">
              <p className="text-sm text-muted-foreground">No tests found for this session.</p>
            </div>
          )}
        </div>

        {/* ── Actions (desktop + non-assessment mobile) ───────────────── */}
        {!isCompleted && !isSkipped && (
          <div className={`mt-8 flex items-center justify-end gap-6 ${isAssessment ? "hidden sm:flex" : "flex"}`}>
            {!isAssessment && (
              <form action={skipAction}>
                <button
                  type="submit"
                  className="font-mono text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors py-2 px-1"
                >
                  skip session
                </button>
              </form>
            )}
            {isAssessment ? (
              <a
                href={`/workouts/${workout.id}/camera`}
                className="inline-flex items-center gap-2 rounded bg-foreground px-6 py-2.5 font-mono text-sm text-background hover:opacity-90 transition-opacity"
              >
                Record →
              </a>
            ) : (
              <form action={completeAction}>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded bg-foreground px-5 py-2.5 font-mono text-sm text-background hover:opacity-90 transition-opacity"
                >
                  Mark session complete →
                </button>
              </form>
            )}
          </div>
        )}

        {/* ── Spacer so sticky bar doesn't cover last card ─────────────── */}
        {isAssessment && !isCompleted && !isSkipped && (
          <div className="h-24 sm:hidden" aria-hidden />
        )}

        {(isCompleted || isSkipped) && (
          <div className="mt-8 flex justify-center">
            <a
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded bg-foreground px-5 py-2.5 font-mono text-sm text-background hover:opacity-90 transition-opacity"
            >
              Back to dashboard →
            </a>
          </div>
        )}

      </div>

      {/* ── Sticky mobile Record bar ──────────────────────────────────────── */}
      {isAssessment && !isCompleted && !isSkipped && (
        <div className="fixed bottom-0 inset-x-0 z-20 border-t border-border bg-background/95 backdrop-blur-sm px-6 py-4 sm:hidden">
          <a
            href={`/workouts/${workout.id}/camera`}
            className="flex w-full items-center justify-center gap-2 rounded bg-foreground py-3.5 font-mono text-sm text-background active:opacity-80 transition-opacity"
          >
            Record →
          </a>
        </div>
      )}

    </main>
  );
}
