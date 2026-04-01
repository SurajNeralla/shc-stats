-- Execute this in the Supabase SQL Editor to update the players table

ALTER TABLE public.players
ADD COLUMN IF NOT EXISTS email text UNIQUE,
ADD COLUMN IF NOT EXISTS password text;
