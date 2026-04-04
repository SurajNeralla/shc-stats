-- Execute this in the Supabase SQL Editor to support accurate batting averages

ALTER TABLE public.match_logs ADD COLUMN IF NOT EXISTS not_out BOOLEAN DEFAULT false;

ALTER TABLE public.player_stats ADD COLUMN IF NOT EXISTS innings_batted INTEGER DEFAULT 0;
ALTER TABLE public.player_stats ADD COLUMN IF NOT EXISTS not_outs INTEGER DEFAULT 0;
ALTER TABLE public.player_stats ADD COLUMN IF NOT EXISTS dismissals INTEGER DEFAULT 0;
