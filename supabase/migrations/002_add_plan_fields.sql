-- ═══════════════════════════════════════════════════════════
-- Migration 002 — Add plan + subscription_status to user_profiles
-- Run this in Supabase SQL Editor AFTER 001_initial_schema.sql
-- ═══════════════════════════════════════════════════════════

-- Add plan column (matches Lemon Squeezy variant names)
ALTER TABLE public.user_profiles
    ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'free'
        CHECK (plan IN ('free', 'signal', 'signal_pro'));

-- Add subscription_status column (mirrors Lemon Squeezy status field)
ALTER TABLE public.user_profiles
    ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'inactive'
        CHECK (subscription_status IN ('active', 'inactive', 'cancelled', 'expired', 'paused', 'past_due', 'unpaid'));

-- Add email column so we can look users up by email in the webhook
-- (Supabase auth.users.email is in auth schema and not directly queryable
--  from service role in all contexts — storing a copy here is simpler)
ALTER TABLE public.user_profiles
    ADD COLUMN IF NOT EXISTS email TEXT;

-- Backfill email from auth.users for any existing rows
UPDATE public.user_profiles p
SET email = u.email
FROM auth.users u
WHERE p.id = u.id
  AND p.email IS NULL;

-- Index for fast webhook lookups by email
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON public.user_profiles(email);

-- Index for fast plan-based queries (e.g. listing all Signal Pro users)
CREATE INDEX IF NOT EXISTS idx_user_profiles_plan ON public.user_profiles(plan);

-- Update the new-user trigger to also copy the email
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
