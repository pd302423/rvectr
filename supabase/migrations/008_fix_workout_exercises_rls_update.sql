-- Add missing UPDATE policy for workout_exercises to allow updating video_path and exercise details
create policy "workout_exercises_update_own" on public.workout_exercises
  for update using (
    exists (
      select 1 from public.workouts w
      where w.id = workout_id and w.user_id = auth.uid()
    )
  );

-- Index logged_sets by user_id for high performance query resolution
create index if not exists logged_sets_user_id_idx on public.logged_sets(user_id, logged_at desc);
