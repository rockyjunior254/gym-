-- =============================================================================
-- STRAKLY GYM MANAGEMENT SYSTEM — COMPLETE CONSOLIDATED ADMIN DATABASE MIGRATION
-- File: database/admin.sql
-- Description: 100% Self-contained PostgreSQL DDL, schema, tables, helper functions,
--              triggers, RLS policies, storage configuration, indexes, foreign key cascades,
--              and administrator elevation.
-- Target Administrator: achiengpatricia32@gmail.com
-- Facility Code: CCS/00104/022
-- =============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 2. CORE DATABASE TABLES (Self-contained, idempotent creation)
-- =============================================================================

-- PROFILES (Core User Identity)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL CHECK (role IN ('admin', 'trainer', 'member')),
    avatar_url TEXT DEFAULT '/static/images/placeholders/avatar-default.svg',
    is_active BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Member Details (Extended athlete metadata)
CREATE TABLE IF NOT EXISTS public.member_details (
    id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    member_number TEXT UNIQUE NOT NULL,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    fitness_goals TEXT,
    medical_notes TEXT,
    joined_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trainer Details (Coaching staff qualifications & bio)
CREATE TABLE IF NOT EXISTS public.trainer_details (
    id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_number TEXT UNIQUE NOT NULL,
    specialisations TEXT[] DEFAULT '{}',
    qualifications TEXT,
    bio TEXT,
    experience_years INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Membership Plans (Subscription tiers)
CREATE TABLE IF NOT EXISTS public.membership_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    duration_type TEXT NOT NULL CHECK (duration_type IN ('daily', 'weekly', 'monthly', 'quarterly', 'annual')),
    duration_days INTEGER NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    benefits JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Member Subscriptions (Athletes enrolled in packages)
CREATE TABLE IF NOT EXISTS public.member_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES public.membership_plans(id) ON DELETE RESTRICT,
    start_date DATE,
    end_date DATE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'frozen', 'cancelled')),
    renewal_count INTEGER DEFAULT 0,
    notes TEXT,
    cancellation_reason TEXT,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cash Payments (Strict Physical Cash Only — Official receipts)
CREATE TABLE IF NOT EXISTS public.cash_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_number TEXT UNIQUE NOT NULL,
    member_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    subscription_id UUID REFERENCES public.member_subscriptions(id) ON DELETE SET NULL,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL DEFAULT 'CASH' CHECK (payment_method = 'CASH'),
    payment_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'reversed', 'corrected', 'completed')),
    notes TEXT,
    correction_reason TEXT,
    reversed_at TIMESTAMPTZ,
    reversed_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Manual Attendance (Strict Front-Desk Lookup Check-in — NO QR/Biometric/Check-out)
CREATE TABLE IF NOT EXISTS public.manual_attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES public.member_subscriptions(id) ON DELETE SET NULL,
    check_in_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'present' CHECK (status IN ('present', 'verified', 'exception', 'corrected', 'denied')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trainer Assignments (Athletes assigned to Coaches)
CREATE TABLE IF NOT EXISTS public.trainer_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'paused')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Facility Services (Personal Training, Group HIIT, Strength Zone, Recovery)
CREATE TABLE IF NOT EXISTS public.services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    category TEXT NOT NULL,
    description TEXT,
    duration_minutes INTEGER,
    price_kes NUMERIC(10, 2) DEFAULT 0.00,
    image_url TEXT,
    benefits JSONB DEFAULT '[]'::jsonb,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_published BOOLEAN DEFAULT TRUE,
    view_count INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fitness Classes (Scheduled Group Sessions)
CREATE TABLE IF NOT EXISTS public.fitness_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT DEFAULT 'Strength',
    description TEXT,
    image_url TEXT,
    trainer_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    class_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    capacity INTEGER NOT NULL DEFAULT 20,
    location TEXT DEFAULT 'Studio A',
    status TEXT NOT NULL DEFAULT 'scheduled',
    is_cancelled BOOLEAN DEFAULT FALSE,
    cancellation_reason TEXT,
    is_published BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Class Bookings
CREATE TABLE IF NOT EXISTS public.class_bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES public.fitness_classes(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    booking_status TEXT NOT NULL DEFAULT 'confirmed' CHECK (booking_status IN ('confirmed', 'cancelled', 'attended', 'no_show')),
    booked_at TIMESTAMPTZ DEFAULT NOW(),
    cancelled_at TIMESTAMPTZ,
    UNIQUE(class_id, member_id)
);

-- Exercise Movement Library
CREATE TABLE IF NOT EXISTS public.exercise_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    target_muscle_group TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Beginner', 'Intermediate', 'Advanced', 'beginner', 'intermediate', 'advanced')),
    equipment_required TEXT,
    instructions TEXT,
    image_url TEXT,
    video_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workout Plans
CREATE TABLE IF NOT EXISTS public.workout_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    goal TEXT,
    difficulty TEXT,
    days_per_week INTEGER DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft', 'active', 'completed', 'archived')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workout Plan Exercises
CREATE TABLE IF NOT EXISTS public.workout_plan_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES public.workout_plans(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES public.exercise_library(id) ON DELETE CASCADE,
    day_of_week TEXT NOT NULL,
    exercise_order INTEGER NOT NULL DEFAULT 1,
    sets INTEGER NOT NULL DEFAULT 3,
    reps TEXT NOT NULL DEFAULT '10-12',
    rest_interval_seconds INTEGER DEFAULT 60,
    notes TEXT
);

-- Workout Logs
CREATE TABLE IF NOT EXISTS public.workout_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    workout_plan_id UUID REFERENCES public.workout_plans(id) ON DELETE SET NULL,
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    title TEXT NOT NULL,
    duration_minutes INTEGER,
    notes TEXT,
    completion_status TEXT NOT NULL DEFAULT 'completed' CHECK (completion_status IN ('completed', 'partial', 'skipped')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fitness Progress Measurements
CREATE TABLE IF NOT EXISTS public.fitness_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    recorded_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    record_date DATE NOT NULL DEFAULT CURRENT_DATE,
    weight_kg NUMERIC(5, 2),
    body_fat_pct NUMERIC(4, 1),
    chest_cm NUMERIC(5, 1),
    waist_cm NUMERIC(5, 1),
    arms_cm NUMERIC(5, 1),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Member Progress Logs (Compatibility alias table)
CREATE TABLE IF NOT EXISTS public.member_progress_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    recorded_date DATE NOT NULL DEFAULT CURRENT_DATE,
    weight_kg NUMERIC(5, 2),
    body_fat_pct NUMERIC(4, 1),
    chest_cm NUMERIC(5, 1),
    waist_cm NUMERIC(5, 1),
    arms_cm NUMERIC(5, 1),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Gym Equipment & Asset Register
CREATE TABLE IF NOT EXISTS public.gym_equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    model_serial TEXT,
    acquisition_date DATE,
    condition TEXT NOT NULL DEFAULT 'excellent' CHECK (condition IN ('excellent', 'good', 'fair', 'needs_maintenance', 'out_of_order')),
    is_available BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    image_url TEXT,
    location TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Equipment Maintenance Logs
CREATE TABLE IF NOT EXISTS public.equipment_maintenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL REFERENCES public.gym_equipment(id) ON DELETE CASCADE,
    reported_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    service_date DATE NOT NULL DEFAULT CURRENT_DATE,
    issue_description TEXT NOT NULL,
    action_taken TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved')),
    cost NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Community Groups
CREATE TABLE IF NOT EXISTS public.community_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    cover_image TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Community Group Members
CREATE TABLE IF NOT EXISTS public.community_group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES public.community_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, user_id)
);

-- Community Posts
CREATE TABLE IF NOT EXISTS public.community_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    group_id UUID REFERENCES public.community_groups(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    image_url TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Community Comments
CREATE TABLE IF NOT EXISTS public.community_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.community_posts(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Community Reactions
CREATE TABLE IF NOT EXISTS public.community_reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.community_posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    reaction_type TEXT NOT NULL DEFAULT 'like' CHECK (reaction_type IN ('like', 'fire', 'muscle', 'clap')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, user_id)
);

-- Community Reports (Moderation)
CREATE TABLE IF NOT EXISTS public.community_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES public.community_posts(id) ON DELETE CASCADE,
    reporter_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed', 'actioned')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notifications
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'general' CHECK (type IN ('general', 'membership', 'payment', 'attendance', 'workout', 'booking', 'announcement', 'community', 'system', 'class')),
    link_url TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Announcements
CREATE TABLE IF NOT EXISTS public.announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    target_role TEXT DEFAULT 'all' CHECK (target_role IN ('all', 'member', 'trainer')),
    is_published BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Logs (Append-Only Governance Trail)
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    actor_role TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    target_id TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    reason TEXT,
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Platform Settings (Key-Value)
CREATE TABLE IF NOT EXISTS public.platform_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 3. SCHEMA MIGRATION & REPAIR (Guarantees clean cascade on delete & no missing cols)
-- =============================================================================
DO $$
BEGIN
    -- profiles
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'is_archived') THEN
        ALTER TABLE public.profiles ADD COLUMN is_archived BOOLEAN DEFAULT false;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'archived_at') THEN
        ALTER TABLE public.profiles ADD COLUMN archived_at TIMESTAMPTZ;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'profiles' AND column_name = 'is_active') THEN
        ALTER TABLE public.profiles ADD COLUMN is_active BOOLEAN DEFAULT true;
    END IF;

    -- member_subscriptions: ensure CASCADE on member delete
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema = 'public' AND constraint_name = 'member_subscriptions_member_id_fkey') THEN
        ALTER TABLE public.member_subscriptions DROP CONSTRAINT member_subscriptions_member_id_fkey;
        ALTER TABLE public.member_subscriptions ADD CONSTRAINT member_subscriptions_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.profiles(id) ON DELETE CASCADE;
    END IF;

    -- cash_payments: ensure SET NULL on member delete so financial books balance
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema = 'public' AND constraint_name = 'cash_payments_member_id_fkey') THEN
        ALTER TABLE public.cash_payments DROP CONSTRAINT cash_payments_member_id_fkey;
        ALTER TABLE public.cash_payments ALTER COLUMN member_id DROP NOT NULL;
        ALTER TABLE public.cash_payments ADD CONSTRAINT cash_payments_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.profiles(id) ON DELETE SET NULL;
    END IF;

    -- manual_attendance: ensure subscription_id exists and status exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'manual_attendance' AND column_name = 'subscription_id') THEN
        ALTER TABLE public.manual_attendance ADD COLUMN subscription_id UUID REFERENCES public.member_subscriptions(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'manual_attendance' AND column_name = 'status') THEN
        ALTER TABLE public.manual_attendance ADD COLUMN status TEXT DEFAULT 'present';
    END IF;

    -- Drop obsolete check_out_time column if present on pre-existing legacy tables
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'manual_attendance' AND column_name = 'check_out_time') THEN
        ALTER TABLE public.manual_attendance DROP COLUMN check_out_time;
    END IF;
END $$;

-- =============================================================================
-- 4. COMPATIBILITY VIEWS (Guarantees zero column mismatch & zero relation errors)
-- =============================================================================
CREATE OR REPLACE VIEW public.payments AS 
SELECT 
    id,
    receipt_number,
    member_id,
    subscription_id,
    amount,
    payment_method,
    payment_date,
    recorded_by,
    status,
    notes,
    correction_reason,
    created_at,
    updated_at
FROM public.cash_payments;

CREATE OR REPLACE VIEW public.attendance AS 
SELECT 
    id,
    member_id,
    subscription_id,
    check_in_time,
    recorded_by,
    status,
    notes,
    created_at
FROM public.manual_attendance;

CREATE OR REPLACE VIEW public.classes AS 
SELECT 
    id,
    name,
    description,
    image_url,
    trainer_id,
    class_date,
    start_time,
    duration_minutes,
    capacity,
    is_published,
    is_cancelled,
    created_at,
    updated_at,
    is_archived,
    cancellation_reason
FROM public.fitness_classes;

CREATE OR REPLACE VIEW public.gym_services AS 
SELECT 
    id,
    name,
    slug,
    category,
    description,
    image_url,
    benefits,
    is_published,
    sort_order,
    created_at,
    is_archived,
    view_count
FROM public.services;

CREATE OR REPLACE VIEW public.equipment_maintenance_logs AS 
SELECT 
    id,
    equipment_id,
    reported_by,
    service_date,
    issue_description,
    action_taken,
    status,
    cost,
    created_at,
    updated_at
FROM public.equipment_maintenance;

CREATE OR REPLACE VIEW public.exercises AS 
SELECT 
    id,
    name,
    category,
    target_muscle_group,
    difficulty,
    equipment_required,
    instructions,
    image_url,
    is_active,
    created_at,
    is_archived,
    video_url
FROM public.exercise_library;

-- =============================================================================
-- 5. ATTENDANCE ELIGIBILITY VALIDATION FUNCTION
-- =============================================================================
DROP FUNCTION IF EXISTS public.check_member_attendance_eligibility(UUID);
CREATE OR REPLACE FUNCTION public.check_member_attendance_eligibility(target_member_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_has_active BOOLEAN := false;
    v_plan_name TEXT := 'None';
    v_end_date DATE;
    v_result JSONB;
BEGIN
    SELECT TRUE, mp.name, ms.end_date
    INTO v_has_active, v_plan_name, v_end_date
    FROM public.member_subscriptions ms
    JOIN public.membership_plans mp ON mp.id = ms.plan_id
    WHERE ms.member_id = target_member_id
      AND ms.status = 'active'
      AND (ms.end_date IS NULL OR ms.end_date >= CURRENT_DATE)
    ORDER BY ms.end_date DESC NULLS FIRST
    LIMIT 1;

    IF v_has_active THEN
        v_result := jsonb_build_object(
            'eligible', TRUE,
            'reason', 'Active subscription found',
            'plan_name', v_plan_name,
            'end_date', v_end_date
        );
    ELSE
        v_result := jsonb_build_object(
            'eligible', FALSE,
            'reason', 'No active or valid subscription found. Awaiting renewal or cash verification at desk.',
            'plan_name', 'None',
            'end_date', NULL
        );
    END IF;

    RETURN v_result;
END;
$$;

-- =============================================================================
-- 6. AUTHORITATIVE ADMIN DASHBOARD KPIS FUNCTION
-- =============================================================================
DROP FUNCTION IF EXISTS public.get_admin_dashboard_kpis();
CREATE OR REPLACE FUNCTION public.get_admin_dashboard_kpis()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_total_members INT := 0;
    v_active_members INT := 0;
    v_expired_members INT := 0;
    v_new_registrations INT := 0;
    v_today_attendance INT := 0;
    v_total_cash NUMERIC(12, 2) := 0.00;
    v_upcoming_classes INT := 0;
    v_active_trainers INT := 0;
    v_result JSONB;
BEGIN
    -- Total Members
    SELECT COUNT(*) INTO v_total_members
    FROM public.profiles
    WHERE role = 'member' AND COALESCE(is_archived, FALSE) = FALSE;

    -- Active Members (unexpired active subscription)
    SELECT COUNT(DISTINCT member_id) INTO v_active_members
    FROM public.member_subscriptions
    WHERE status = 'active'
      AND (end_date IS NULL OR end_date >= CURRENT_DATE);

    -- Expired Memberships
    SELECT COUNT(DISTINCT member_id) INTO v_expired_members
    FROM public.member_subscriptions
    WHERE status = 'expired'
       OR (status = 'active' AND end_date < CURRENT_DATE);

    -- New Registrations in the last 30 days
    SELECT COUNT(*) INTO v_new_registrations
    FROM public.profiles
    WHERE role = 'member'
      AND created_at >= (NOW() - INTERVAL '30 days');

    -- Today's Attendance Check-ins (from manual_attendance)
    SELECT COUNT(*) INTO v_today_attendance
    FROM public.manual_attendance
    WHERE check_in_time::DATE = CURRENT_DATE;

    -- Physical Cash Collected (strictly from cash_payments)
    SELECT COALESCE(SUM(amount), 0.00) INTO v_total_cash
    FROM public.cash_payments
    WHERE status IN ('completed', 'confirmed');

    -- Upcoming Classes (from fitness_classes)
    SELECT COUNT(*) INTO v_upcoming_classes
    FROM public.fitness_classes
    WHERE class_date >= CURRENT_DATE
      AND is_cancelled = FALSE;

    -- Active Trainers on Staff
    SELECT COUNT(*) INTO v_active_trainers
    FROM public.profiles
    WHERE role = 'trainer'
      AND is_active = TRUE
      AND COALESCE(is_archived, FALSE) = FALSE;

    v_result := jsonb_build_object(
        'total_members', v_total_members,
        'active_members', v_active_members,
        'expired_memberships', v_expired_members,
        'new_registrations', v_new_registrations,
        'today_attendance', v_today_attendance,
        'total_cash_collected', v_total_cash,
        'upcoming_classes', v_upcoming_classes,
        'active_trainers', v_active_trainers
    );

    RETURN v_result;
END;
$$;

-- =============================================================================
-- 7. APPEND-ONLY SECURITY AUDIT TRIGGER
-- =============================================================================
DROP TRIGGER IF EXISTS trg_prevent_audit_modification ON public.audit_logs;
DROP FUNCTION IF EXISTS public.prevent_audit_log_modification() CASCADE;

CREATE OR REPLACE FUNCTION public.prevent_audit_log_modification()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Audit log entries are strictly append-only and cannot be updated or deleted.';
END;
$$;

CREATE TRIGGER trg_prevent_audit_modification
BEFORE UPDATE OR DELETE ON public.audit_logs
FOR EACH ROW
EXECUTE FUNCTION public.prevent_audit_log_modification();

-- =============================================================================
-- 8. STORAGE BUCKETS CONFIGURATION (Safe Setup)
-- =============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'buckets') THEN
        INSERT INTO storage.buckets (id, name, public)
        VALUES 
            ('gym-public', 'gym-public', true),
            ('avatars', 'avatars', true),
            ('gym_media', 'gym_media', true),
            ('service_images', 'service_images', true),
            ('equipment_images', 'equipment_images', true),
            ('community-uploads', 'community-uploads', true)
        ON CONFLICT (id) DO UPDATE SET public = true;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Storage bucket creation handled via Supabase dashboard: %', SQLERRM;
END $$;

-- Storage Policies
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'objects') THEN
        DROP POLICY IF EXISTS "Public view for media" ON storage.objects;
        CREATE POLICY "Public view for media"
        ON storage.objects FOR SELECT
        USING (bucket_id IN ('gym-public', 'avatars', 'gym_media', 'service_images', 'equipment_images', 'community-uploads'));

        DROP POLICY IF EXISTS "Authenticated users upload media" ON storage.objects;
        CREATE POLICY "Authenticated users upload media"
        ON storage.objects FOR INSERT
        TO authenticated
        WITH CHECK (bucket_id IN ('gym-public', 'avatars', 'gym_media', 'service_images', 'equipment_images', 'community-uploads'));
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Storage policy configuration handled via Supabase dashboard: %', SQLERRM;
END $$;

-- =============================================================================
-- 9. ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================
ALTER TABLE public.services ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.equipment_maintenance ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public can view published services" ON public.services;
CREATE POLICY "Public can view published services"
ON public.services FOR SELECT
USING (is_published = true AND is_archived = false);

DROP POLICY IF EXISTS "Admins full management of services" ON public.services;
CREATE POLICY "Admins full management of services"
ON public.services FOR ALL
TO authenticated
USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Admins full management of equipment maintenance" ON public.equipment_maintenance;
CREATE POLICY "Admins full management of equipment maintenance"
ON public.equipment_maintenance FOR ALL
TO authenticated
USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
);

-- =============================================================================
-- 10. SAFE IDEMPOTENT ELEVATION OF ADMINISTRATOR ACCOUNT
-- =============================================================================
-- Promotes achiengpatricia32@gmail.com to 'admin' using the existing Supabase Auth UUID
INSERT INTO public.profiles (id, email, full_name, role, is_active, is_archived)
SELECT 
    id,
    email,
    'Strakly Administrator',
    'admin',
    true,
    false
FROM auth.users
WHERE lower(email) = lower('achiengpatricia32@gmail.com')
ON CONFLICT (id) 
DO UPDATE SET
    role = 'admin',
    is_active = true,
    is_archived = false,
    full_name = 'Strakly Administrator';

-- Fallback insertion if auth.users is populated separately
INSERT INTO public.profiles (id, email, full_name, role, is_active, is_archived)
VALUES ('b16ba989-8b00-40e3-ad82-9b6e397342a3', 'achiengpatricia32@gmail.com', 'Strakly Administrator', 'admin', true, false)
ON CONFLICT (id) DO UPDATE SET role = 'admin', is_active = true, is_archived = false;

-- =============================================================================
-- 11. INDEXES FOR HIGH-TRAFFIC ADMINISTRATIVE QUERIES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_cash_payments_status_date ON public.cash_payments(status, payment_date);
CREATE INDEX IF NOT EXISTS idx_manual_attendance_checkin ON public.manual_attendance(check_in_time);
CREATE INDEX IF NOT EXISTS idx_subs_member_status ON public.member_subscriptions(member_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON public.audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_role_active ON public.profiles(role, is_active);
CREATE INDEX IF NOT EXISTS idx_fitness_classes_date ON public.fitness_classes(class_date, is_cancelled);

-- =============================================================================
-- 12. INITIAL STRAKLY PLATFORM SETTINGS
-- =============================================================================
INSERT INTO public.platform_settings (key, value)
VALUES 
    ('general', jsonb_build_object(
        'gym_name', 'Strakly Fitness Facility',
        'tagline', 'High-Performance Iron, Discipline & Athletic Conditioning',
        'address', 'Strakly Athletic Facility, Wing B, Nairobi',
        'phone', '+254 700 123 456',
        'email', 'info@strakly.com',
        'opening_hours', 'Mon - Sat: 05:00 - 22:00 | Sun: 08:00 - 18:00',
        'currency', 'KES'
    )),
    ('rules', jsonb_build_object(
        'payment_rule', 'CASH ONLY — All transactions recorded and receipted at the reception desk.',
        'attendance_rule', 'MANUAL ONLY — Authorised front-desk check-in upon membership verification.',
        'coaching_policy', 'Assigned coaches construct tailored progressive overload protocols.'
    ))
ON CONFLICT (key) 
DO UPDATE SET value = EXCLUDED.value;
