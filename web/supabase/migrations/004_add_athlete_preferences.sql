-- Migration: Add athlete preferences to profiles table
-- Adds experience_level and training_style columns

ALTER TABLE profiles
ADD COLUMN experience_level TEXT CHECK (experience_level IN ('Beginner', 'Intermediate', 'Advanced', 'Not sure')),
ADD COLUMN training_style TEXT CHECK (training_style IN ('Strength', 'Hypertrophy', 'Endurance', 'Skill', 'Not sure'));
