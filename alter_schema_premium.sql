-- Premium Scoring Architecture Schema Additions

CREATE TABLE IF NOT EXISTS public.matches (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    match_number integer NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    locked boolean DEFAULT false
);

CREATE TABLE IF NOT EXISTS public.entries (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    match_id uuid REFERENCES public.matches(id) ON DELETE CASCADE,
    player_id uuid REFERENCES public.players(id) ON DELETE CASCADE,
    score numeric NOT NULL,
    fantasy_points numeric NOT NULL,
    rank integer
);

ALTER TABLE public.players
ADD COLUMN IF NOT EXISTS total_score numeric DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_fantasy_points numeric DEFAULT 0;

ALTER TABLE public.entries
ADD COLUMN IF NOT EXISTS fantasy_points numeric DEFAULT 0;
