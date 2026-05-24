"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { profileSchema, type ProfileInput } from "./schema";

export type SaveProfileResult =
  | { ok: true }
  | { ok: false; error: string };

export async function saveProfile(input: ProfileInput): Promise<SaveProfileResult> {
  const parsed = profileSchema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Invalid input" };
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return { ok: false, error: "Not signed in" };
  }

  const { error } = await supabase
    .from("profiles")
    .update({
      display_name: parsed.data.display_name,
      days_per_week: parsed.data.days_per_week,
      session_minutes: parsed.data.session_minutes,
      equipment: parsed.data.equipment,
      current_skills: parsed.data.current_skills,
      goal_skills: parsed.data.goal_skills,
      injuries: parsed.data.injuries || null,
      onboarded: true,
    })
    .eq("id", user.id);

  if (error) {
    console.error("[onboarding] update profile error:", error);
    return { ok: false, error: error.message };
  }

  revalidatePath("/dashboard");
  redirect("/dashboard");
}
