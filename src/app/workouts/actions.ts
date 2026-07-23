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

  // 1. Check generation limit to prevent abuse (Hard cap of 100 generations per user ~ $0.05 max spend on cheap models)
  const { data: usageCheck } = await supabase
    .from("profiles")
    .select("generation_count")
    .eq("id", user.id)
    .single();

  if (usageCheck && usageCheck.generation_count >= 100) {
    throw new Error("You have reached the maximum AI generation limit for your account.");
  }

  // Generate (uses Claude when ANTHROPIC_API_KEY is set; mock otherwise)
  const generated = await generateWorkout(athleteProfile, focus);

  // Increment generation count
  await supabase
    .from("profiles")
    .update({ generation_count: (usageCheck?.generation_count || 0) + 1 })
    .eq("id", user.id);

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
  videoPathsOrFormData: Record<string, string | number> | FormData = {},
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

  // Update each exercise with its corresponding manual reps or video paths
  if (!(videoPathsOrFormData instanceof FormData)) {
    const data = videoPathsOrFormData as Record<string, string | number>;

    // Verify exercise ownership to prevent unauthorized cross-tenant modifications
    const { data: validExercises } = await supabase
      .from("workout_exercises")
      .select("id")
      .eq("workout_id", workoutId);

    const validExerciseIds = new Set(validExercises?.map((e) => e.id) ?? []);

    // Insert into logged_sets or update video_path
    for (const [exerciseId, val] of Object.entries(data)) {
      if (!validExerciseIds.has(exerciseId)) {
        continue; // Skip any unauthorized or invalid exercise IDs
      }

      if (typeof val === "number" && val >= 0) {
        await supabase.from("logged_sets").insert({
          workout_exercise_id: exerciseId,
          user_id: user.id,
          set_number: 1,
          reps_completed: Math.floor(val),
          rpe_reported: 10,
        });
      } else if (typeof val === "string" && val.length > 0) {
        await supabase
          .from("workout_exercises")
          .update({ video_path: val })
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
