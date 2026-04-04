-- Run this in your Supabase SQL editor
ALTER TABLE public.player_stats
ADD COLUMN IF NOT EXISTS man_of_match INTEGER DEFAULT 0;
