-- Add gamification columns to profiles table
ALTER TABLE profiles
ADD COLUMN xp INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN credits INTEGER DEFAULT 100 NOT NULL,
ADD COLUMN league TEXT DEFAULT 'Bronze' NOT NULL;
