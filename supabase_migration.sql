-- ============================================================
-- Smart School ID Attendance Scanner — Supabase Migration
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- ── Users table ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.users (
    id            BIGSERIAL PRIMARY KEY,
    custom_id     TEXT UNIQUE NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student'
                  CHECK (role IN ('student', 'teacher', 'staff')),
    photo_url     TEXT,
    parent_phone  TEXT,
    parent_email  TEXT,
    secret_key    TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── Attendance logs table ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.attendance_logs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    scan_type   TEXT NOT NULL CHECK (scan_type IN ('TIME_IN', 'TIME_OUT')),
    scanned_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_logs_user_id    ON public.attendance_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_scanned_at ON public.attendance_logs(scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_custom_id ON public.users(custom_id);

-- ── Row Level Security (enable but allow service-role full access) ──
ALTER TABLE public.users           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attendance_logs ENABLE ROW LEVEL SECURITY;

-- Allow service role (backend) unrestricted access
CREATE POLICY "service_role_users" ON public.users
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "service_role_logs" ON public.attendance_logs
    FOR ALL USING (auth.role() = 'service_role');

-- ── Demo seed data ────────────────────────────────────────────
-- Replace secret_key values with output of: python -c "
--   import hmac, hashlib, base64, os
--   master = os.getenv('MASTER_SECRET','change_me')
--   cid = 'STU001'
--   print(base64.b32encode(hmac.new(master.encode(), cid.encode(), hashlib.sha256).digest()).decode())
-- "
INSERT INTO public.users (custom_id, full_name, role, parent_phone, parent_email, secret_key)
VALUES
  ('STU001', 'Alice Reyes',  'student', '+639171234567', 'alice@example.com', 'REPLACE_WITH_GENERATED_SECRET'),
  ('STU002', 'Bob Santos',   'student', '+639179876543', 'bob@example.com',   'REPLACE_WITH_GENERATED_SECRET'),
  ('TCH001', 'Ms. Cruz',     'teacher', '+639175551234', 'cruz@example.com',  'REPLACE_WITH_GENERATED_SECRET')
ON CONFLICT (custom_id) DO NOTHING;
