-- Run this in the Supabase SQL Editor to fix broken image URLs
-- Maps each player name to their local static image path

UPDATE public.players SET image_url = '/static/images/suraj.jpg.jpeg'  WHERE LOWER(name) LIKE '%suraj%';
UPDATE public.players SET image_url = '/static/images/sashank.jpeg'    WHERE LOWER(name) LIKE '%sashank%';
UPDATE public.players SET image_url = '/static/images/saran.jpeg'      WHERE LOWER(name) LIKE '%saran%';
UPDATE public.players SET image_url = '/static/images/abhi.jpeg'       WHERE LOWER(name) LIKE '%abhi%';
UPDATE public.players SET image_url = '/static/images/deepu.jpeg'      WHERE LOWER(name) LIKE '%deepu%' OR LOWER(name) LIKE '%kl_%';
UPDATE public.players SET image_url = '/static/images/sunny.jpeg'      WHERE LOWER(name) LIKE '%sunny%';
UPDATE public.players SET image_url = '/static/images/pavan.jpeg'      WHERE LOWER(name) LIKE '%pavan%';
UPDATE public.players SET image_url = '/static/images/prabhas.jpeg'    WHERE LOWER(name) LIKE '%prabhas%';
UPDATE public.players SET image_url = '/static/images/sailesh.jpeg'    WHERE LOWER(name) LIKE '%sailesh%';
