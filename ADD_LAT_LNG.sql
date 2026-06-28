-- Run this in your Supabase Dashboard SQL Editor to support map coordinates storage
ALTER TABLE pet_owners ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE pet_owners ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
