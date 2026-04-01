-- Live Match Module Schema

CREATE TABLE IF NOT EXISTS public.live_matches (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    team_a_name text NOT NULL,
    team_b_name text NOT NULL,
    toss_winner text, -- 'team_a' or 'team_b'
    toss_decision text, -- 'bat' or 'bowl'
    current_innings integer DEFAULT 1,
    team_a_score integer DEFAULT 0,
    team_a_wickets integer DEFAULT 0,
    team_a_balls integer DEFAULT 0,
    team_b_score integer DEFAULT 0,
    team_b_wickets integer DEFAULT 0,
    team_b_balls integer DEFAULT 0,
    target integer,
    total_overs integer DEFAULT 20,
    status text DEFAULT 'setup', -- 'setup', 'innings_1', 'innings_2', 'completed'
    match_result text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.live_match_players (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    live_match_id uuid REFERENCES public.live_matches(id) ON DELETE CASCADE,
    player_id uuid REFERENCES public.players(id) ON DELETE CASCADE,
    match_log_id uuid REFERENCES public.match_logs(id) ON DELETE SET NULL,
    team text NOT NULL, -- 'team_a' or 'team_b'
    status text DEFAULT 'waiting', -- 'waiting', 'batting', 'out', 'bowling'
    is_striker boolean DEFAULT false,
    is_non_striker boolean DEFAULT false,
    is_current_bowler boolean DEFAULT false,
    runs_scored integer DEFAULT 0,
    balls_faced integer DEFAULT 0,
    fours integer DEFAULT 0,
    sixes integer DEFAULT 0,
    balls_bowled integer DEFAULT 0,
    runs_conceded integer DEFAULT 0,
    wickets_taken integer DEFAULT 0,
    maidens integer DEFAULT 0
);

-- Optional Table to log delivery by delivery explicitly (useful for advanced timeline playback)
CREATE TABLE IF NOT EXISTS public.live_match_balls (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    live_match_id uuid REFERENCES public.live_matches(id) ON DELETE CASCADE,
    innings integer,
    over_number integer,
    ball_number integer,
    striker_id uuid REFERENCES public.players(id),
    non_striker_id uuid REFERENCES public.players(id),
    bowler_id uuid REFERENCES public.players(id),
    runs integer DEFAULT 0,
    extras integer DEFAULT 0,
    extra_type text, -- 'wide', 'no-ball', or null
    is_wicket boolean DEFAULT false,
    wicket_type text, -- 'bowled', 'caught', 'run-out', etc.
    created_at timestamp with time zone DEFAULT now()
);

-- If you already ran this script previously without total_overs, run this line:
ALTER TABLE public.live_matches ADD COLUMN IF NOT EXISTS total_overs INTEGER DEFAULT 20;
