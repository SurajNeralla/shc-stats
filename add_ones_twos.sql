-- Add 'ones' and 'twos' to player_stats
ALTER TABLE public.player_stats 
ADD COLUMN IF NOT EXISTS ones INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS twos INTEGER DEFAULT 0;

-- Add 'ones' and 'twos' to match_logs
ALTER TABLE public.match_logs 
ADD COLUMN IF NOT EXISTS ones INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS twos INTEGER DEFAULT 0;

-- Add 'ones' and 'twos' to live_match_players
ALTER TABLE public.live_match_players 
ADD COLUMN IF NOT EXISTS ones INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS twos INTEGER DEFAULT 0;
