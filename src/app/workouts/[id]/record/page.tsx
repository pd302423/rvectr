import { redirect, notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSkill } from "@/lib/calisthenics";
import { completeWorkout } from "@/app/workouts/actions";
import { RecordSubmit } from "./record-submit";

export default async function RecordPage({
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
  if (workout.session_focus !== "assessment") redirect(`/workouts/${id}`);

  const { data: exercises } = await supabase
    .from("workout_exercises")
    .select("id, exercise_slug, order_index")
    .eq("workout_id", id)
    .order("order_index", { ascending: true });

  const rows = (exercises ?? []).map((ex) => ({
    id: ex.id,
    slug: ex.exercise_slug,
    name: getSkill(ex.exercise_slug)?.label ?? ex.exercise_slug.replace(/_/g, " "),
    order_index: ex.order_index,
  }));

  const submitAction = completeWorkout.bind(null, workout.id);

  return (
    <main className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-3xl">

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <header className="mb-10 border-b border-border pb-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
                § Assessment recording
              </p>
              <h1
                style={{ fontFamily: "var(--font-serif)" }}
                className="mt-3 text-4xl leading-tight tracking-tight"
              >
                Upload recordings
              </h1>
              <p className="mt-2 text-sm text-muted-foreground max-w-md leading-relaxed">
                Record each test on your phone, then upload below. The CV model grades
                every rep for form quality — results drive your training programme.
              </p>
            </div>
            <a
              href={`/workouts/${id}`}
              className="font-mono text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors shrink-0 -mr-2 px-2 py-2"
            >
              ← tests
            </a>
          </div>
        </header>

        {/* ── General recording tips ──────────────────────────────────────── */}
        <div className="mb-8 rounded border border-border bg-card p-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">
            Recording checklist
          </p>
          <div className="grid grid-cols-1 gap-px bg-border border border-border rounded overflow-hidden sm:grid-cols-2">
            {[
              { n: "01", label: "Stable camera", body: "Use a stand, lean against a wall, or prop on a shelf. Handheld will blur the rep and invalidate CV grading." },
              { n: "02", label: "Continuous take", body: "Record the full set in one take without stopping. Start recording before the first rep, stop after the last." },
              { n: "03", label: "2 takes per test", body: "Record twice. Upload your cleanest attempt. More reps in the uploaded video is not better — one complete set is enough." },
              { n: "04", label: "Good lighting", body: "Face a window or ensure strong indoor lighting behind the camera. Shadows on your body hide joint angles from the CV model." },
              { n: "05", label: "Full body in frame", body: "Every test requires a specific framing — check the guide on the previous page. Partial framing will reduce grading accuracy." },
              { n: "06", label: "Format", body: "MP4 or MOV preferred. 1080p minimum. Landscape or portrait both work. Files recorded on iPhone or Android upload fine." },
            ].map(({ n, label, body }) => (
              <div key={n} className="bg-card p-4">
                <p className="font-mono text-[10px] text-muted-foreground/40 mb-1">{n}</p>
                <p className="text-xs font-semibold text-foreground mb-1">{label}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ── Per-exercise upload (client component) ─────────────────────── */}
        <RecordSubmit workoutId={id} exercises={rows} submitAction={submitAction} />

      </div>
    </main>
  );
}
