-- Add generation tracking to profiles
ALTER TABLE public.profiles 
ADD COLUMN generation_count integer DEFAULT 0 NOT NULL;
