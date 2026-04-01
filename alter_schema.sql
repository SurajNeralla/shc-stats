-- Execute this in the Supabase SQL Editor to add the Match Logs table

CREATE TABLE IF NOT EXISTS public.match_logs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  player_id uuid REFERENCES public.players(id) ON DELETE CASCADE,
  match_date date DEFAULT CURRENT_DATE,
  opponent text DEFAULT 'Unknown',
  
  -- Batting
  runs integer DEFAULT 0,
  balls_faced integer DEFAULT 0,
  fours integer DEFAULT 0,
  sixes integer DEFAULT 0,
  
  -- Bowling
  overs_bowled numeric(5,1) DEFAULT 0,
  maidens integer DEFAULT 0,
  runs_conceded integer DEFAULT 0,
  wickets integer DEFAULT 0,
  no_balls integer DEFAULT 0,
  wides integer DEFAULT 0,
  
  -- Fielding
  catches integer DEFAULT 0,
  stumpings integer DEFAULT 0
);
