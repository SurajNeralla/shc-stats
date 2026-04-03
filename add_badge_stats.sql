ALTER TABLE public.player_stats
ADD COLUMN IF NOT EXISTS thirties integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS three_wkt_hauls integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS five_fives integer DEFAULT 0;
