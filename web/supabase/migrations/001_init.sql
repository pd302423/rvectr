-- ============================================================================
-- FormCoach — Initial schema
-- Paste this into Supabase SQL Editor (Dashboard → SQL Editor → New query).
-- ============================================================================

-- ---------- ENUMS ----------
create type experience_level as enum ('beginner', 'intermediate', 'advanced');

-- ---------- PROFILES ----------
-- Extends auth.users with FormCoach-specific fields.
create table public.profiles (
  id                uuid primary key references auth.users(id) on delete cascade,
  display_name      text,
  experience_level  experience_level,
  -- Skills the user can currently perform (e.g., ['pull_up', 'push_up', 'l_sit'])
  current_skills    text[] default '{}',
  -- Skills the user is working toward (e.g., ['muscle_up', 'planche_lean'])
  goal_skills       text[] default '{}',
  -- Equipment available (e.g., ['pull_up_bar', 'rings', 'parallettes', 'none'])
  equipment         text[] default '{}',
  days_per_week     int check (days_per_week between 1 and 7),
  session_minutes   int check (session_minutes between 10 and 240),
  injuries          text,
  -- Set to true once the onboarding form is submitted.
  onboarded         boolean not null default false,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

-- Auto-update updated_at on row changes.
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Auto-create a blank profile row whenever someone signs up.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, display_name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', new.email)
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- ROW-LEVEL SECURITY ----------
alter table public.profiles enable row level security;

create policy "profiles_self_select"
  on public.profiles for select
  using (auth.uid() = id);

create policy "profiles_self_update"
  on public.profiles for update
  using (auth.uid() = id);

create policy "profiles_self_insert"
  on public.profiles for insert
  with check (auth.uid() = id);
