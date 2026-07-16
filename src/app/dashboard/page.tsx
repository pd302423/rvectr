import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSkill } from "@/lib/calisthenics";
import { generateSession } from "@/app/workouts/actions";
import { GenerateButton } from "./generate-button";
import { Trophy, Zap, Coins, Snowflake, Star, Check, Lock, Play } from "lucide-react";
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

  // Calculate streak from completed workouts
  const completedWorkoutsResult = await supabase
    .from("workouts")
    .select("completed_at")
    .eq("user_id", user.id)
    .eq("status", "completed")
    .order("completed_at", { ascending: false });
    
  const completedDates = (completedWorkoutsResult.data ?? [])
    .map(w => w.completed_at ? new Date(w.completed_at).toDateString() : null)
    .filter(Boolean) as string[];
    
  // Unique dates only
  const uniqueDates = [...new Set(completedDates)];
  
  let currentStreak = 0;
  const todayStr = new Date().toDateString();
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toDateString();

  if (uniqueDates.length > 0) {
    if (uniqueDates[0] === todayStr || uniqueDates[0] === yesterdayStr) {
      currentStreak = 1;
      let checkDate = new Date(uniqueDates[0]);
      
      for (let i = 1; i < uniqueDates.length; i++) {
        checkDate.setDate(checkDate.getDate() - 1);
        if (uniqueDates[i] === checkDate.toDateString()) {
          currentStreak++;
        } else {
          break;
        }
      }
    }
  }

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
                <span className={`text-2xl font-bold font-mono ${currentStreak > 0 ? 'text-orange-500' : 'text-muted-foreground'}`}>
                  {currentStreak > 0 ? '🔥' : '❄️'} {currentStreak}
                </span>
                <span className="text-sm font-medium text-muted-foreground">Day{currentStreak !== 1 ? 's' : ''}</span>
              </div>
            </div>
            <div className="flex gap-2">
              {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, idx) => {
                const todayIdx = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;
                const isToday = idx === todayIdx;
                
                // For past days this week, check if we had a workout
                const d = new Date();
                d.setDate(d.getDate() - (todayIdx - idx));
                const isCompleted = uniqueDates.includes(d.toDateString());
                
                return (
                  <div key={idx} className={`w-8 h-10 flex flex-col items-center justify-center rounded-lg border ${isToday ? 'bg-foreground text-background border-foreground' : isCompleted ? 'bg-orange-500/10 border-orange-500/30 text-orange-600' : 'bg-background border-border text-muted-foreground/30'}`}>
                    <span className="text-[10px] font-mono font-bold">{day}</span>
                    {isCompleted && !isToday && <span className="text-[8px] mt-1">🔥</span>}
                    {isToday && <span className="w-1 h-1 bg-background rounded-full mt-1"></span>}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2">
            <div className="flex flex-col items-center justify-center bg-card border border-border rounded-xl p-3 shadow-sm">
              <Zap className="w-5 h-5 text-amber-500 mb-1" />
              <span className="text-lg font-mono tracking-tight">{xp}</span>
              <span className="text-[9px] font-mono uppercase text-muted-foreground tracking-widest mt-1">Total XP</span>
            </div>
            <div className="flex flex-col items-center justify-center bg-card border border-border rounded-xl p-3 shadow-sm">
              <Coins className="w-5 h-5 text-sky-500 mb-1" />
              <span className="text-lg font-mono tracking-tight">{credits}</span>
              <span className="text-[9px] font-mono uppercase text-muted-foreground tracking-widest mt-1">Credits</span>
            </div>
            <div className="flex flex-col items-center justify-center bg-card border border-border rounded-xl p-3 shadow-sm">
              <Snowflake className="w-5 h-5 text-blue-400 mb-1" />
              <span className="text-lg font-mono tracking-tight">2</span>
              <span className="text-[9px] font-mono uppercase text-muted-foreground tracking-widest mt-1">Freezes</span>
            </div>
            <div className="flex flex-col items-center justify-center bg-card border border-border rounded-xl p-3 shadow-sm">
              <Trophy className="w-5 h-5 text-emerald-500 mb-1" />
              <span className="text-md font-mono tracking-tight">{league}</span>
              <span className="text-[9px] font-mono uppercase text-muted-foreground tracking-widest mt-1">League</span>
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

        {/* ── The Path (Duolingo Style) ─────────────────────────────────────────────── */}
        {hasAssessment ? (
          <div className="mb-24 flex flex-col items-center relative py-8 w-full max-w-sm mx-auto">
            {[...Array(10)].map((_, i) => {
              // Note: workoutCount includes the assessment. So day 1 is actually workout 2.
              const nodeIndex = i;
              const isCompleted = nodeIndex < workoutCount - 1;
              const isCurrent = nodeIndex === workoutCount - 1;
              const isLocked = nodeIndex > workoutCount - 1;
              
              // Zig-zag offset pattern
              const offsetPattern = [0, 40, 60, 40, 0, -40, -60, -40];
              const offset = offsetPattern[i % offsetPattern.length];
              const nextOffset = offsetPattern[(i + 1) % offsetPattern.length];
              
              return (
                <div key={i} className="relative flex justify-center items-center h-28 w-full">
                  {/* Connection Line */}
                  {i < 9 && (
                    <svg className="absolute top-1/2 left-0 w-full h-28 -z-10 overflow-visible pointer-events-none">
                      <line 
                        x1={`calc(50% + ${offset}px)`} 
                        y1="24" 
                        x2={`calc(50% + ${nextOffset}px)`} 
                        y2="136" 
                        stroke={isCompleted ? "#0ea5e9" : "#334155"} 
                        strokeWidth="12" 
                        strokeLinecap="round"
                      />
                    </svg>
                  )}
                  
                  <div 
                    className={`relative w-20 h-20 rounded-full border-b-[6px] flex items-center justify-center cursor-pointer transition-transform hover:scale-105 active:scale-95 ${
                      isCompleted ? 'bg-sky-500 border-sky-700 text-white' : 
                      isCurrent ? 'bg-emerald-500 border-emerald-700 text-white animate-bounce' : 
                      'bg-card border-border text-muted-foreground grayscale'
                    }`}
                    style={{ transform: `translateX(${offset}px)` }}
                  >
                    {isCompleted ? <Check className="w-8 h-8" /> : isCurrent ? <Star className="w-8 h-8 fill-current" /> : <Lock className="w-6 h-6 opacity-50" />}
                    
                    {/* Floating label for current day */}
                    {isCurrent && (
                      <div className="absolute -top-10 bg-background border border-border px-3 py-1 rounded-full text-xs font-bold whitespace-nowrap shadow-sm text-foreground animate-pulse">
                        START TODAY
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="mb-10 rounded-2xl border border-sky-500/30 bg-sky-500/10 p-6 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-2">
                  Step 1 — baseline assessment
                </p>
                <p className="font-medium text-sky-900 dark:text-sky-100">
                  Begin your strength assessment
                </p>
                <p className="mt-1 text-xs text-sky-800 dark:text-sky-200/70">
                  rvector will generate a personalised test battery to measure your actual baseline.
                </p>
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

        {/* ── Fixed Bottom CTA ─────────────────────────────────────────────── */}
        <div className="fixed bottom-[80px] left-0 right-0 p-4 bg-gradient-to-t from-background via-background/95 to-transparent z-40 flex justify-center pb-6">
          <form action={generateSession} className="w-full max-w-sm">
            <button
              type="submit"
              className="w-full h-14 rounded-2xl bg-foreground text-background font-bold text-lg border-b-[6px] border-foreground/70 active:border-b-0 active:translate-y-[6px] transition-all flex items-center justify-center gap-3 shadow-xl"
            >
              <Play className="w-6 h-6 fill-current" />
              {hasAssessment ? "Start Today's Session" : "Begin Assessment"}
            </button>
          </form>
        </div>

      </div>
    </main>
  );
}
