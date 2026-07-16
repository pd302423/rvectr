import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSkill } from "@/lib/calisthenics";
import { generateSession } from "@/app/workouts/actions";
import { GenerateButton } from "./generate-button";
import { Trophy, Zap, Coins } from "lucide-react";
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
  completed: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  in_progress: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
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

  const xp = profile.xp ?? 0;
  const credits = profile.credits ?? 100;
  const league = profile.league ?? 'Bronze';

  return (
    <main className="min-h-screen bg-background px-4 py-8 pb-24">
      <div className="mx-auto max-w-4xl">

        {/* ── Gamification Header ────────────────────────────────────────── */}
        <header className="mb-10 flex flex-col gap-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground mb-1">
                § Athlete dashboard
              </p>
              <h1 style={{ fontFamily: "var(--font-serif)" }} className="text-4xl leading-tight tracking-tight">
                {profile.display_name}
              </h1>
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="text-xs text-muted-foreground border border-border rounded-full px-3 py-0.5">
                  {profile.days_per_week}d/wk · {profile.session_minutes}min
                </span>
                {hasAssessment ? (
                  <span className="text-xs border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 rounded-full px-3 py-0.5">
                    ✓ Assessment Complete
                  </span>
                ) : (
                  <span className="text-xs border border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300 rounded-full px-3 py-0.5">
                    Baseline Pending
                  </span>
                )}
              </div>
            </div>
            <form action="/auth/signout" method="POST">
              <button type="submit" className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground/50 hover:text-muted-foreground transition-colors px-2 py-2">
                Sign out
              </button>
            </form>
          </div>

          <div className="flex items-center justify-between bg-card border border-border rounded-2xl p-4 shadow-sm mb-2">
            <div className="flex flex-col">
              <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest">Current Streak</span>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-2xl font-bold font-mono text-orange-500">🔥 3</span>
                <span className="text-sm font-medium text-muted-foreground">Days</span>
              </div>
            </div>
            <div className="flex gap-2">
              {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, idx) => {
                const isToday = idx === new Date().getDay() - 1 || (idx === 6 && new Date().getDay() === 0);
                const isCompleted = idx < 3; // Mocking past days as completed
                return (
                  <div key={idx} className={`w-8 h-10 flex flex-col items-center justify-center rounded-lg border ${isToday ? 'bg-foreground text-background border-foreground' : isCompleted ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600' : 'bg-background border-border text-muted-foreground'}`}>
                    <span className="text-[10px] font-mono font-bold">{day}</span>
                    {isCompleted && !isToday && <span className="text-[8px] mt-1">✓</span>}
                    {isToday && <span className="w-1 h-1 bg-background rounded-full mt-1"></span>}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col items-center justify-center bg-card border border-border rounded-2xl p-4 shadow-sm">
              <Zap className="w-5 h-5 text-amber-500 mb-2" />
              <span className="text-xl font-mono tracking-tight">{xp}</span>
              <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest mt-1">Total XP</span>
            </div>
            <div className="flex flex-col items-center justify-center bg-card border border-border rounded-2xl p-4 shadow-sm">
              <Coins className="w-5 h-5 text-sky-500 mb-2" />
              <span className="text-xl font-mono tracking-tight">{credits}</span>
              <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest mt-1">Credits</span>
            </div>
            <div className="flex flex-col items-center justify-center bg-card border border-border rounded-2xl p-4 shadow-sm">
              <Trophy className="w-5 h-5 text-emerald-500 mb-2" />
              <span className="text-lg font-mono tracking-tight">{league}</span>
              <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-widest mt-1">League</span>
            </div>
          </div>
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
        <div className={`mb-10 rounded-2xl border p-6 shadow-sm ${hasAssessment ? "border-border bg-card" : "border-sky-500/30 bg-sky-500/10"}`}>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-2">
                {hasAssessment ? "Next session ready" : "Step 1 — baseline assessment"}
              </p>
              <p className={`font-medium ${hasAssessment ? "text-foreground" : "text-sky-900 dark:text-sky-100"}`}>
                {hasAssessment ? "Generate tomorrow's workout" : "Begin your strength assessment"}
              </p>
              <p className={`mt-1 text-xs ${hasAssessment ? "text-muted-foreground" : "text-sky-800 dark:text-sky-200/70"}`}>
                {hasAssessment
                  ? "rvector AI will auto-regulate volume based on your recent performance."
                  : "rvector will generate a personalised test battery to measure your actual baseline."}
              </p>
            </div>
            <form action={generateSession} className="shrink-0">
              <GenerateButton focusLabel={hasAssessment ? "Generate Workout" : "Assessment"} />
            </form>
          </div>
        </div>

        {/* ── Training Roadmap ─────────────────────────────────────────────── */}
        {hasAssessment && (
          <div className="mb-10 relative">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-4 px-1">
              Training Block Roadmap
            </p>
            <div className="relative py-4 px-2">
              <div className="absolute top-0 bottom-0 left-[27px] w-0.5 bg-border -z-10"></div>
              
              <div className="flex items-start gap-4 mb-8">
                <div className="w-10 h-10 rounded-full bg-emerald-500 text-background flex items-center justify-center font-bold text-sm shrink-0 border-4 border-background shadow-sm">✓</div>
                <div className="bg-card border border-border rounded-xl p-4 flex-1 shadow-sm opacity-60">
                  <h3 className="font-semibold text-sm">Baseline Assessment</h3>
                  <p className="text-xs text-muted-foreground mt-1">Calibrated max capacities and kinematic profile.</p>
                </div>
              </div>

              <div className="flex items-start gap-4 mb-8">
                <div className="w-10 h-10 rounded-full bg-sky-500 text-background flex items-center justify-center font-bold text-sm shrink-0 border-4 border-background shadow-md shadow-sky-500/20">W1</div>
                <div className="bg-card border-2 border-sky-500/30 rounded-xl p-4 flex-1 shadow-md">
                  <div className="flex justify-between items-start mb-1">
                    <h3 className="font-semibold text-sm">Accumulation Phase</h3>
                    <span className="text-[10px] uppercase tracking-widest text-sky-500 font-bold font-mono">Current</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Building tissue tolerance and mastering movement patterns at sub-maximal loads.</p>
                </div>
              </div>

              <div className="flex items-start gap-4 mb-8 opacity-50 grayscale">
                <div className="w-10 h-10 rounded-full bg-muted text-muted-foreground flex items-center justify-center font-bold text-sm shrink-0 border-4 border-background">W2</div>
                <div className="bg-card border border-border rounded-xl p-4 flex-1 shadow-sm">
                  <h3 className="font-semibold text-sm">Intensification Phase</h3>
                  <p className="text-xs text-muted-foreground mt-1">Increasing load and approaching mechanical failure on key lifts.</p>
                </div>
              </div>

              <div className="flex items-start gap-4 opacity-50 grayscale">
                <div className="w-10 h-10 rounded-full bg-muted text-muted-foreground flex items-center justify-center font-bold text-sm shrink-0 border-4 border-background">W3</div>
                <div className="bg-card border border-border rounded-xl p-4 flex-1 shadow-sm">
                  <h3 className="font-semibold text-sm">Realisation (Peak)</h3>
                  <p className="text-xs text-muted-foreground mt-1">Testing new maxes and demonstrating acquired strength.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Recent workouts ──────────────────────────────────────────────── */}
        {recentWorkouts.length > 0 && (
          <div className="mb-10">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3 px-1">
              Session history
            </p>
            <div className="space-y-2">
              {recentWorkouts.map((w, i) => (
                <a
                  key={w.id}
                  href={`/workouts/${w.id}`}
                  className={`flex items-center justify-between gap-4 bg-card px-5 py-4 rounded-2xl border border-border shadow-sm hover:border-foreground/20 hover:shadow-md transition-all`}
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
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 mb-8">

          {/* Current skills */}
          <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
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
                No baseline skills recorded. rvector will programme foundations.
              </p>
            )}
          </div>

          {/* Goal skills */}
          <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
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
            <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
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
            <div className="bg-card p-6 rounded-2xl border border-border shadow-sm">
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
