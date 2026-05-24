import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSkill } from "@/lib/calisthenics";
import { generateSession } from "@/app/workouts/actions";
import { GenerateButton } from "./generate-button";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const FOCUS_LABELS: Record<string, string> = {
  strength: "Strength",
  skill: "Skill Acquisition",
  volume: "Volume",
  legs: "Legs",
};

const BLOCK_LABELS: Record<string, string> = {
  accumulation: "Accumulation",
  intensification: "Intensification",
  realisation: "Realisation",
  deload: "Deload",
};

const STATUS_STYLES: Record<string, string> = {
  completed: "border-emerald-300 bg-emerald-50 text-emerald-700",
  in_progress: "border-amber-200 bg-amber-50 text-amber-700",
  pending: "border-border text-muted-foreground",
  skipped: "border-border text-muted-foreground/50",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");

  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  if (!profile?.onboarded) redirect("/onboarding");

  // Assessment phase — count how many assessments have been done
  const countResult = await supabase
    .from("workouts")
    .select("*", { count: "exact", head: true })
    .eq("user_id", user.id);

  const workoutCount = countResult.count ?? 0;
  const hasAssessment = workoutCount > 0;

  // Recent workouts (last 5) — tables may not exist yet if migration pending
  const workoutsResult = await supabase
    .from("workouts")
    .select("id, session_focus, block, week_number, status, generated_at, completed_at")
    .eq("user_id", user.id)
    .order("generated_at", { ascending: false })
    .limit(5);
  const recentWorkouts = workoutsResult.data ?? [];

  return (
    <main className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-4xl">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <header className="mb-12 flex items-start justify-between border-b border-border pb-8">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
              § Athlete dashboard
            </p>
            <h1
              style={{ fontFamily: "var(--font-serif)" }}
              className="mt-3 text-4xl leading-tight tracking-tight"
            >
              {profile.display_name}
            </h1>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="text-xs text-muted-foreground border border-border rounded px-2 py-0.5">
                {profile.days_per_week}d/wk · {profile.session_minutes}min
              </span>
              {hasAssessment ? (
                <span className="text-xs border border-emerald-200 bg-emerald-50 text-emerald-700 rounded px-2 py-0.5">
                  ✓ assessment complete
                </span>
              ) : (
                <span className="text-xs border border-sky-200 bg-sky-50 text-sky-700 rounded px-2 py-0.5">
                  baseline · pending assessment
                </span>
              )}
            </div>
          </div>
          <form action="/auth/signout" method="POST">
            <button
              type="submit"
              className="font-mono text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors"
            >
              sign out
            </button>
          </form>
        </header>

        {/* ── Error notice ────────────────────────────────────────────────── */}
        {error && (
          <div className="mb-6 rounded border border-red-200 bg-red-50 p-4">
            <p className="font-mono text-xs text-red-700">
              Session generation failed: {decodeURIComponent(error)}. Ensure the workouts migration has been run in Supabase.
            </p>
          </div>
        )}

        {/* ── Assessment CTA ───────────────────────────────────────────────── */}
        <div className={`mb-8 rounded border p-6 ${hasAssessment ? "border-border bg-card" : "border-sky-200 bg-sky-50"}`}>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-2">
                {hasAssessment ? "Reassessment" : "Step 1 — baseline assessment"}
              </p>
              <p className={`font-medium ${hasAssessment ? "text-foreground" : "text-sky-900"}`}>
                {hasAssessment ? "Run another strength assessment" : "Begin your strength assessment"}
              </p>
              <p className={`mt-1 text-xs ${hasAssessment ? "text-muted-foreground" : "text-sky-800"}`}>
                {hasAssessment
                  ? "Vector will generate a fresh diagnostic test based on your current profile."
                  : "Vector will generate a personalised test battery to measure your actual baseline. Takes ~30 minutes with full rest between tests."}
              </p>
            </div>
            <form action={generateSession} className="shrink-0">
              <GenerateButton focusLabel={hasAssessment ? "Reassessment" : "Assessment"} />
            </form>
          </div>
        </div>

        {/* ── Recent workouts ──────────────────────────────────────────────── */}
        {recentWorkouts.length > 0 && (
          <div className="mb-8">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">
              Session history
            </p>
            <div className="space-y-px rounded border border-border overflow-hidden">
              {recentWorkouts.map((w, i) => (
                <a
                  key={w.id}
                  href={`/workouts/${w.id}`}
                  className={`flex items-center justify-between gap-4 bg-card px-4 py-3 hover:bg-muted/30 transition-colors ${
                    i !== 0 ? "border-t border-border" : ""
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="font-mono text-xs text-muted-foreground/50 shrink-0">
                      #{recentWorkouts.length - i}
                    </span>
                    <span className="text-sm text-foreground truncate">
                      {FOCUS_LABELS[w.session_focus] ?? w.session_focus}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground hidden sm:inline">
                      {BLOCK_LABELS[w.block] ?? w.block} · Wk {w.week_number}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="font-mono text-[10px] text-muted-foreground hidden sm:inline">
                      {formatDate(w.generated_at)}
                    </span>
                    <span
                      className={`font-mono text-[10px] uppercase tracking-wider border rounded px-2 py-0.5 ${
                        STATUS_STYLES[w.status] ?? STATUS_STYLES.pending
                      }`}
                    >
                      {w.status}
                    </span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* ── Athlete data grid ────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-px border border-border sm:grid-cols-2">

          {/* Current skills */}
          <div className="bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
              Current skill inventory
            </p>
            {profile.current_skills?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {profile.current_skills.map((slug: string) => (
                  <span
                    key={slug}
                    className="text-xs border border-border rounded px-2 py-0.5 text-foreground"
                  >
                    {getSkill(slug)?.label ?? slug}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                No baseline skills recorded. Vector will programme foundations.
              </p>
            )}
          </div>

          {/* Goal skills */}
          <div className="bg-card p-5">
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
              Target skill objectives
            </p>
            {profile.goal_skills?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {profile.goal_skills.map((slug: string) => (
                  <span
                    key={slug}
                    className="text-xs border border-emerald-300 bg-emerald-50 rounded px-2 py-0.5 text-emerald-700"
                  >
                    {getSkill(slug)?.label ?? slug}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No targets set.</p>
            )}
          </div>

          {/* Equipment */}
          {profile.equipment?.length > 0 && (
            <div className="bg-card p-5">
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
                Available equipment
              </p>
              <div className="flex flex-wrap gap-1.5">
                {profile.equipment.map((eq: string) => (
                  <span
                    key={eq}
                    className="text-xs border border-border rounded px-2 py-0.5 text-muted-foreground"
                  >
                    {eq.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Injuries */}
          {profile.injuries && (
            <div className="bg-card p-5">
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-3">
                Contraindications / notes
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {profile.injuries}
              </p>
            </div>
          )}

        </div>

      </div>
    </main>
  );
}
