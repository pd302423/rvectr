-- 002_workouts.sql
-- Workout generation tables for Vector
-- Run in Supabase SQL editor after 001_init.sql

-- ── Workouts ─────────────────────────────────────────────────────────────────
create table if not exists public.workouts (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references auth.users(id) on delete cascade,
  generated_at     timestamptz not null default now(),
  session_focus    text not null,          -- 'strength' | 'skill' | 'volume' | 'legs'
  week_number      integer,               -- week in current mesocycle
  block            text,                  -- 'accumulation' | 'intensification' | 'realisation' | 'deload'
  ai_rationale     text,                  -- coach explanation paragraph
  status           text not null default 'pending', -- 'pending' | 'in_progress' | 'completed' | 'skipped'
  completed_at     timestamptz,
  created_at       timestamptz not null default now()
);

-- ── Workout exercises ─────────────────────────────────────────────────────────
create table if not exists public.workout_exercises (
  id                  uuid primary key default gen_random_uuid(),
  workout_id          uuid not null references public.workouts(id) on delete cascade,
  exercise_slug       text not null,
  order_index         integer not null,
  intent              text not null,       -- 'strength' | 'hypertrophy' | 'skill_acquisition' | 'tendon_prep' | 'active_recovery'
  target_sets         integer not null,
  target_reps_min     integer not null,
  target_reps_max     integer not null,
  rest_seconds_min    integer not null,
  rest_seconds_max    integer not null,
  tempo               text,               -- e.g. '30X0' (eccentric-pause-concentric-pause)
  biomechanical_note  text,               -- clinical cue for this exercise
  progression_context text,               -- where this sits in the larger skill journey
  created_at          timestamptz not null default now()
);

-- ── Logged sets (Week 3 — logging UI) ────────────────────────────────────────
create table if not exists public.logged_sets (
  id                  uuid primary key default gen_random_uuid(),
  workout_exercise_id uuid not null references public.workout_exercises(id) on delete cascade,
  user_id             uuid not null references auth.users(id) on delete cascade,
  set_number          integer not null,
  reps_completed      integer,
  hold_seconds        integer,            -- for isometric movements
  rpe_reported        integer,            -- 1–10, self-reported
  form_score          numeric(3,2),       -- 0.00–1.00, from CV classifier (Week 6)
  notes               text,
  logged_at           timestamptz not null default now()
);

-- ── Row Level Security ────────────────────────────────────────────────────────
alter table public.workouts          enable row level security;
alter table public.workout_exercises enable row level security;
alter table public.logged_sets       enable row level security;

-- workouts: own rows only
create policy "workouts_select_own" on public.workouts
  for select using (auth.uid() = user_id);
create policy "workouts_insert_own" on public.workouts
  for insert with check (auth.uid() = user_id);
create policy "workouts_update_own" on public.workouts
  for update using (auth.uid() = user_id);

-- workout_exercises: visible if parent workout belongs to user
create policy "workout_exercises_select_own" on public.workout_exercises
  for select using (
    exists (
      select 1 from public.workouts w
      where w.id = workout_id and w.user_id = auth.uid()
    )
  );
create policy "workout_exercises_insert_own" on public.workout_exercises
  for insert with check (
    exists (
      select 1 from public.workouts w
      where w.id = workout_id and w.user_id = auth.uid()
    )
  );

-- logged_sets: own rows only
create policy "logged_sets_select_own" on public.logged_sets
  for select using (auth.uid() = user_id);
create policy "logged_sets_insert_own" on public.logged_sets
  for insert with check (auth.uid() = user_id);
create policy "logged_sets_update_own" on public.logged_sets
  for update using (auth.uid() = user_id);

-- ── Indexes ───────────────────────────────────────────────────────────────────
create index if not exists workouts_user_id_idx on public.workouts(user_id, generated_at desc);
create index if not exists workout_exercises_workout_id_idx on public.workout_exercises(workout_id, order_index);
create index if not exists logged_sets_workout_exercise_id_idx on public.logged_sets(workout_exercise_id);
