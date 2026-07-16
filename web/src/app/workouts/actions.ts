"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { generateWorkout } from "@/lib/anthropic";
import type { SessionFocus } from "@/lib/knowledge/overcoming_gravity";

// ─── Generate & persist a new workout session ────────────────────────────────

export async function generateSession() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");

  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  if (!profile?.onboarded) redirect("/onboarding");

  // Count all workouts for this user — drives the OG rotation
  const { count } = await supabase
    .from("workouts")
    .select("*", { count: "exact", head: true })
    .eq("user_id", user.id);

  const totalWorkouts = count ?? 0;

  // Phase 1: always run an assessment until CV grading is live (Week 6).
  // After CV grading, switch to OG session rotation.
  const focus: SessionFocus = "assessment";

  const athleteProfile = {
    display_name: profile.display_name,
    days_per_week: profile.days_per_week,
    session_minutes: profile.session_minutes,
    equipment: profile.equipment ?? [],
    current_skills: profile.current_skills ?? [],
    goal_skills: profile.goal_skills ?? [],
    experience_level: profile.experience_level ?? "Not sure",
    training_style: profile.training_style ?? "Not sure",
    injuries: profile.injuries ?? null,
    total_workouts_completed: totalWorkouts,
  };

  // Generate (uses Claude when ANTHROPIC_API_KEY is set; mock otherwise)
  const generated = await generateWorkout(athleteProfile, focus);

  // Persist workout row
  const { data: workout, error: wErr } = await supabase
    .from("workouts")
    .insert({
      user_id: user.id,
      session_focus: generated.session_focus,
      week_number: generated.week_number,
      block: generated.block,
      ai_rationale: generated.ai_rationale,
      status: "pending",
    })
    .select()
    .single();

  if (wErr || !workout) {
    redirect(`/dashboard?error=${encodeURIComponent(wErr?.message ?? "save_failed")}`);
  }

  // Persist exercises
  if (generated.exercises.length > 0) {
    await supabase.from("workout_exercises").insert(
      generated.exercises.map((ex) => ({
        workout_id: workout.id,
        exercise_slug: ex.exercise_slug,
        order_index: ex.order_index,
        intent: ex.intent,
        target_sets: ex.target_sets,
        target_reps_min: ex.target_reps_min,
        target_reps_max: ex.target_reps_max,
        rest_seconds_min: ex.rest_seconds_min,
        rest_seconds_max: ex.rest_seconds_max,
        tempo: ex.tempo,
        biomechanical_note: ex.biomechanical_note,
        progression_context: ex.progression_context,
      })),
    );
  }

  redirect(`/workouts/${workout.id}`);
}

// ─── Mark a workout complete ─────────────────────────────────────────────────

export async function completeWorkout(
  workoutId: string,
  videoPathsOrFormData: Record<string, string> | FormData = {},
) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");

  // Update workout status
  const { error: wErr } = await supabase
    .from("workouts")
    .update({
      status: "completed",
      completed_at: new Date().toISOString(),
    })
    .eq("id", workoutId)
    .eq("user_id", user.id);

  if (wErr) {
    throw new Error(`Failed to complete workout: ${wErr.message}`);
  }

  // Update each exercise with its corresponding video_path (if not called from HTML form action)
  if (!(videoPathsOrFormData instanceof FormData)) {
    for (const [exerciseId, path] of Object.entries(videoPathsOrFormData)) {
      if (path) {
        await supabase
          .from("workout_exercises")
          .update({ video_path: path })
          .eq("id", exerciseId)
          .eq("workout_id", workoutId);
      }
    }
  }

  redirect("/dashboard");
}

// ─── Skip a pending workout ──────────────────────────────────────────────────

export async function skipWorkout(workoutId: string) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/signin");

  await supabase
    .from("workouts")
    .update({ status: "skipped" })
    .eq("id", workoutId)
    .eq("user_id", user.id);

  redirect("/dashboard");
}
