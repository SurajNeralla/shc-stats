-- Execute this in the Supabase SQL Editor
CREATE TABLE IF NOT EXISTS public.players (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  name text NOT NULL,
  age integer,
  team text,
  role text,
  image_url text
);

CREATE TABLE IF NOT EXISTS public.player_stats (
  player_id uuid REFERENCES public.players(id) ON DELETE CASCADE PRIMARY KEY,
  matches integer DEFAULT 0,
  catches integer DEFAULT 0,
  stumpings integer DEFAULT 0,
  -- Batting
  runs integer DEFAULT 0,
  balls_faced integer DEFAULT 0,
  fours integer DEFAULT 0,
  sixes integer DEFAULT 0,
  fifties integer DEFAULT 0,
  hundreds integer DEFAULT 0,
  highest_score integer DEFAULT 0,
  -- Bowling
  overs_bowled numeric(5,1) DEFAULT 0,
  maidens integer DEFAULT 0,
  runs_conceded integer DEFAULT 0,
  wickets integer DEFAULT 0,
  no_balls integer DEFAULT 0,
  wides integer DEFAULT 0
);
