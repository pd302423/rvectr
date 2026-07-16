-- 003_video_uploads.sql
-- Migration to support direct client-side video uploads to Supabase Storage
-- and associate video file paths with workout exercises.

-- 1. Add video_path column to workout_exercises table
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 
    FROM information_schema.columns 
    WHERE table_schema = 'public' 
      AND table_name = 'workout_exercises' 
      AND column_name = 'video_path'
  ) THEN
    ALTER TABLE public.workout_exercises ADD COLUMN video_path TEXT;
  END IF;
END $$;

-- 2. Create the assessment-videos storage bucket
-- Supabase Storage stores metadata in the storage.buckets table.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'assessment-videos', 
  'assessment-videos', 
  FALSE, 
  104857600, -- 100 MB in bytes (100 * 1024 * 1024)
  '{video/mp4,video/quicktime,video/hevc,video/webm}'
)
ON CONFLICT (id) DO UPDATE SET
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 3. Enable RLS and define Storage Row Level Security (RLS) policies
-- Note: storage.objects RLS is enabled by default in Supabase.
-- These policies use the helper function `storage.foldername(name)` 
-- to check if the root folder matches the user's authenticated ID.

CREATE POLICY "Allow authenticated users to upload to their own folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'assessment-videos' 
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Allow authenticated users to read their own uploaded files"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'assessment-videos' 
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Allow authenticated users to delete their own uploaded files"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'assessment-videos' 
  AND (storage.foldername(name))[1] = auth.uid()::text
);
