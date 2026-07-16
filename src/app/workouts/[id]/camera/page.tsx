import { redirect, notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSkill } from "@/lib/calisthenics";
import { completeWorkout } from "@/app/workouts/actions";
import { CameraFlow } from "./camera-flow";

export default async function CameraPage({
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
    <main className="min-h-screen bg-black text-white overflow-hidden">
      <CameraFlow exercises={rows} submitAction={submitAction} />
    </main>
  );
}
