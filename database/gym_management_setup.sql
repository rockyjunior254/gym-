-- ============================================================================
-- LEVY KIRINYA GYM MANAGEMENT SYSTEM (CCS/00104/022)
-- MASTER SUPABASE DATABASE ARCHITECTURE SETUP SCRIPT
-- ============================================================================
-- This script configures the relational PostgreSQL schema, tables, foreign keys,
-- indexes, triggers, Row Level Security (RLS) policies, and initial configuration.
--
-- EXECUTION INSTRUCTIONS:
-- 1. Open your Supabase Project Dashboard (https://supabase.com/dashboard)
-- 2. Navigate to SQL Editor -> New Query
-- 3. Paste the entire contents of this file and click "Run"
-- 4. Verify in Table Editor that all tables were created successfully
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. PROFILES & ROLES (Tied to Supabase auth.users)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL CHECK (role IN ('admin', 'trainer', 'member')),
    avatar_url TEXT DEFAULT '/static/images/placeholders/avatar-default.svg',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Member specific extensions
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

-- Trainer specific extensions
CREATE TABLE IF NOT EXISTS public.trainer_details (
    id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_number TEXT UNIQUE NOT NULL,
    specialisations TEXT[] DEFAULT '{}',
    qualifications TEXT,
    bio TEXT,
    experience_years INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 2. MEMBERSHIP PACKAGES & SUBSCRIPTIONS
-- ============================================================================
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.member_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    plan_id UUID NOT NULL REFERENCES public.membership_plans(id) ON DELETE RESTRICT,
    start_date DATE,
    end_date DATE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'frozen', 'cancelled')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 3. CASH PAYMENTS & RECEIPTS (STRICT CASH ONLY)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.cash_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receipt_number TEXT UNIQUE NOT NULL,
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    subscription_id UUID REFERENCES public.member_subscriptions(id) ON DELETE SET NULL,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL DEFAULT 'CASH' CHECK (payment_method = 'CASH'),
    payment_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'reversed', 'corrected')),
    notes TEXT,
    correction_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 4. MANUAL ATTENDANCE (STRICTLY NO QR / SCANNING)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.manual_attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    subscription_id UUID REFERENCES public.member_subscriptions(id) ON DELETE SET NULL,
    check_in_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'present' CHECK (status IN ('present', 'exception', 'corrected')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 5. TRAINER ASSIGNMENT (Coached Member vs Self-Guided)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.trainer_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'terminated')),
    assigned_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 6. SERVICES (Configurable for Homepage)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    benefits JSONB DEFAULT '[]'::jsonb,
    is_published BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 7. CLASSES & BOOKINGS
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.fitness_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    trainer_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    class_date DATE NOT NULL,
    start_time TIME NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    capacity INTEGER NOT NULL DEFAULT 20,
    is_published BOOLEAN DEFAULT TRUE,
    is_cancelled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.class_bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES public.fitness_classes(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    booking_status TEXT NOT NULL DEFAULT 'confirmed' CHECK (booking_status IN ('confirmed', 'cancelled', 'attended', 'no_show')),
    booked_at TIMESTAMPTZ DEFAULT NOW(),
    cancelled_at TIMESTAMPTZ,
    UNIQUE(class_id, member_id)
);

-- ============================================================================
-- 8. EXERCISE LIBRARY & WORKOUT PLANS
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.exercise_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    target_muscle_group TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Beginner', 'Intermediate', 'Advanced')),
    equipment_required TEXT,
    instructions TEXT,
    image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.workout_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    goal TEXT,
    difficulty TEXT,
    days_per_week INTEGER DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft', 'active', 'completed', 'archived')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.workout_plan_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES public.workout_plans(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES public.exercise_library(id) ON DELETE RESTRICT,
    day_of_week TEXT NOT NULL,
    exercise_order INTEGER NOT NULL DEFAULT 1,
    sets INTEGER NOT NULL DEFAULT 3,
    reps TEXT NOT NULL DEFAULT '10-12',
    rest_interval_seconds INTEGER DEFAULT 60,
    notes TEXT
);

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

-- ============================================================================
-- 9. FITNESS PROGRESS MEASUREMENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.fitness_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    recorded_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    record_date DATE NOT NULL DEFAULT CURRENT_DATE,
    weight_kg NUMERIC(5, 2),
    body_fat_pct NUMERIC(4, 1),
    chest_cm NUMERIC(5, 1),
    waist_cm NUMERIC(5, 1),
    arms_cm NUMERIC(5, 1),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 10. EQUIPMENT & MAINTENANCE
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.gym_equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    model_serial TEXT,
    acquisition_date DATE,
    condition TEXT NOT NULL DEFAULT 'excellent' CHECK (condition IN ('excellent', 'good', 'fair', 'needs_maintenance', 'out_of_order')),
    is_available BOOLEAN DEFAULT TRUE,
    image_url TEXT,
    location TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.equipment_maintenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL REFERENCES public.gym_equipment(id) ON DELETE CASCADE,
    reported_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    service_date DATE NOT NULL DEFAULT CURRENT_DATE,
    issue_description TEXT NOT NULL,
    action_taken TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved')),
    cost NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 11. COMMUNITY HUB (SHARED ACROSS ADMIN, TRAINER & MEMBER)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.community_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    cover_image TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.community_group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES public.community_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, user_id)
);

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

CREATE TABLE IF NOT EXISTS public.community_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.community_posts(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.community_reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES public.community_posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    reaction_type TEXT NOT NULL DEFAULT 'like' CHECK (reaction_type IN ('like', 'fire', 'muscle', 'clap')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, user_id)
);

CREATE TABLE IF NOT EXISTS public.community_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES public.community_posts(id) ON DELETE CASCADE,
    reporter_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed', 'actioned')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.private_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 12. NOTIFICATIONS & ANNOUNCEMENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'general' CHECK (type IN ('general', 'membership', 'payment', 'attendance', 'workout', 'booking', 'announcement', 'community')),
    link_url TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    target_role TEXT DEFAULT 'all' CHECK (target_role IN ('all', 'member', 'trainer')),
    is_published BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 13. AUDIT LOGS (APPEND-ONLY)
-- ============================================================================
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

-- ============================================================================
-- 14. PLATFORM SETTINGS (Key-Value)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.platform_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);
CREATE INDEX IF NOT EXISTS idx_member_subscriptions_member ON public.member_subscriptions(member_id);
CREATE INDEX IF NOT EXISTS idx_member_subscriptions_status ON public.member_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_cash_payments_member ON public.cash_payments(member_id);
CREATE INDEX IF NOT EXISTS idx_cash_payments_receipt ON public.cash_payments(receipt_number);
CREATE INDEX IF NOT EXISTS idx_manual_attendance_member ON public.manual_attendance(member_id);
CREATE INDEX IF NOT EXISTS idx_manual_attendance_date ON public.manual_attendance(check_in_time);
CREATE INDEX IF NOT EXISTS idx_trainer_assignments_trainer ON public.trainer_assignments(trainer_id);
CREATE INDEX IF NOT EXISTS idx_trainer_assignments_member ON public.trainer_assignments(member_id);
CREATE INDEX IF NOT EXISTS idx_fitness_classes_date ON public.fitness_classes(class_date);
CREATE INDEX IF NOT EXISTS idx_class_bookings_class ON public.class_bookings(class_id);
CREATE INDEX IF NOT EXISTS idx_class_bookings_member ON public.class_bookings(member_id);
CREATE INDEX IF NOT EXISTS idx_workout_plans_member ON public.workout_plans(member_id);
CREATE INDEX IF NOT EXISTS idx_workout_logs_member ON public.workout_logs(member_id);
CREATE INDEX IF NOT EXISTS idx_fitness_progress_member ON public.fitness_progress(member_id);
CREATE INDEX IF NOT EXISTS idx_community_posts_author ON public.community_posts(author_id);
CREATE INDEX IF NOT EXISTS idx_private_messages_pair ON public.private_messages(sender_id, receiver_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON public.notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON public.audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_date ON public.audit_logs(created_at);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trainer_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.membership_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cash_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.manual_attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trainer_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.services ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fitness_classes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.class_bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercise_library ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_plan_exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fitness_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gym_equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.equipment_maintenance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_reactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.private_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_settings ENABLE ROW LEVEL SECURITY;

-- Helper function to check admin role
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Profiles: Public read active profiles, users update own profile, admin manages all
CREATE POLICY "Public read active profiles" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "Users update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Admins full profile access" ON public.profiles FOR ALL USING (public.is_admin());

-- Plans & Services: Public read published, admin manage
CREATE POLICY "Anyone read active plans" ON public.membership_plans FOR SELECT USING (is_active = true OR public.is_admin());
CREATE POLICY "Admin manage plans" ON public.membership_plans FOR ALL USING (public.is_admin());

CREATE POLICY "Anyone read published services" ON public.services FOR SELECT USING (is_published = true OR public.is_admin());
CREATE POLICY "Admin manage services" ON public.services FOR ALL USING (public.is_admin());

-- Subscriptions: Member view own, admin manage all
CREATE POLICY "Member view own subscriptions" ON public.member_subscriptions FOR SELECT USING (auth.uid() = member_id OR public.is_admin());
CREATE POLICY "Admin manage subscriptions" ON public.member_subscriptions FOR ALL USING (public.is_admin());

-- Cash Payments: Member view own, staff/admin manage
CREATE POLICY "Member view own cash receipts" ON public.cash_payments FOR SELECT USING (auth.uid() = member_id OR public.is_admin());
CREATE POLICY "Admin manage cash payments" ON public.cash_payments FOR ALL USING (public.is_admin());

-- Attendance: Member view own, staff/admin manage
CREATE POLICY "Member view own attendance" ON public.manual_attendance FOR SELECT USING (auth.uid() = member_id OR public.is_admin());
CREATE POLICY "Admin manage attendance" ON public.manual_attendance FOR ALL USING (public.is_admin());

-- Classes & Bookings: Anyone read classes, member book own
CREATE POLICY "Anyone read classes" ON public.fitness_classes FOR SELECT USING (true);
CREATE POLICY "Admin manage classes" ON public.fitness_classes FOR ALL USING (public.is_admin());
CREATE POLICY "Member manage own bookings" ON public.class_bookings FOR ALL USING (auth.uid() = member_id OR public.is_admin());

-- Exercise Library: Authenticated read, admin manage
CREATE POLICY "Anyone read exercises" ON public.exercise_library FOR SELECT USING (true);
CREATE POLICY "Admin manage exercises" ON public.exercise_library FOR ALL USING (public.is_admin());

-- Workout Plans: Member view assigned, assigned trainer manage, admin manage
CREATE POLICY "Workout plan access" ON public.workout_plans FOR ALL USING (
    auth.uid() = member_id OR auth.uid() = trainer_id OR public.is_admin()
);
CREATE POLICY "Workout plan exercises access" ON public.workout_plan_exercises FOR ALL USING (
    EXISTS (
        SELECT 1 FROM public.workout_plans p
        WHERE p.id = workout_plan_exercises.plan_id
        AND (p.member_id = auth.uid() OR p.trainer_id = auth.uid() OR public.is_admin())
    )
);

-- Workout Logs: Member view/create own, assigned trainer view, admin manage
CREATE POLICY "Workout logs access" ON public.workout_logs FOR ALL USING (
    auth.uid() = member_id OR public.is_admin() OR EXISTS (
        SELECT 1 FROM public.trainer_assignments ta
        WHERE ta.member_id = workout_logs.member_id AND ta.trainer_id = auth.uid() AND ta.status = 'active'
    )
);

-- Fitness Progress: Member view own, assigned trainer view/create, admin manage
CREATE POLICY "Fitness progress access" ON public.fitness_progress FOR ALL USING (
    auth.uid() = member_id OR public.is_admin() OR EXISTS (
        SELECT 1 FROM public.trainer_assignments ta
        WHERE ta.member_id = fitness_progress.member_id AND ta.trainer_id = auth.uid() AND ta.status = 'active'
    )
);

-- Equipment: All view available, admin manage
CREATE POLICY "All view equipment" ON public.gym_equipment FOR SELECT USING (true);
CREATE POLICY "Admin manage equipment" ON public.gym_equipment FOR ALL USING (public.is_admin());
CREATE POLICY "Staff manage maintenance" ON public.equipment_maintenance FOR ALL USING (
    public.is_admin() OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'trainer'))
);

-- Community Posts & Comments: Members, Trainers & Admin read/post
CREATE POLICY "Read public community posts" ON public.community_posts FOR SELECT USING (is_hidden = false OR author_id = auth.uid() OR public.is_admin());
CREATE POLICY "Create community posts" ON public.community_posts FOR INSERT WITH CHECK (auth.uid() = author_id);
CREATE POLICY "Manage own community posts" ON public.community_posts FOR UPDATE USING (auth.uid() = author_id OR public.is_admin());

CREATE POLICY "Read comments" ON public.community_comments FOR SELECT USING (true);
CREATE POLICY "Create comments" ON public.community_comments FOR INSERT WITH CHECK (auth.uid() = author_id);

CREATE POLICY "Manage reactions" ON public.community_reactions FOR ALL USING (auth.uid() = user_id OR public.is_admin());
CREATE POLICY "Create reports" ON public.community_reports FOR INSERT WITH CHECK (auth.uid() = reporter_id);
CREATE POLICY "Admin review reports" ON public.community_reports FOR ALL USING (public.is_admin());

-- Private Messages: Sender & receiver only
CREATE POLICY "Private messages access" ON public.private_messages FOR ALL USING (
    auth.uid() = sender_id OR auth.uid() = receiver_id
);

-- Notifications: User view and update own
CREATE POLICY "User notifications access" ON public.notifications FOR ALL USING (auth.uid() = user_id);

-- Announcements: Everyone read published, admin manage
CREATE POLICY "Read published announcements" ON public.announcements FOR SELECT USING (is_published = true OR public.is_admin());
CREATE POLICY "Admin manage announcements" ON public.announcements FOR ALL USING (public.is_admin());

-- Audit Logs: Admin read-only, insert permitted
CREATE POLICY "Admin read audit logs" ON public.audit_logs FOR SELECT USING (public.is_admin());
CREATE POLICY "System insert audit logs" ON public.audit_logs FOR INSERT WITH CHECK (true);

-- Platform Settings: Public read, admin manage
CREATE POLICY "Public read platform settings" ON public.platform_settings FOR SELECT USING (true);
CREATE POLICY "Admin manage platform settings" ON public.platform_settings FOR ALL USING (public.is_admin());

-- ============================================================================
-- INITIAL PLATFORM SETTINGS & SEED DATA
-- ============================================================================
INSERT INTO public.platform_settings (key, value)
VALUES
    ('general', '{
        "gym_name": "Levy Kirinya Elite Gym",
        "tagline": "TRAIN HARD. STAY STRONG. OWN YOUR PROGRESS.",
        "description": "Train with purpose, build strength and track your fitness journey with an elite gym experience designed around your goals.",
        "address": "Kirinya Road, Facility Wing B, Nairobi",
        "phone": "+254 700 123 456",
        "email": "info@levygym.co.ke",
        "opening_hours": {
            "weekdays": "05:00 AM - 10:00 PM",
            "saturdays": "06:00 AM - 09:00 PM",
            "sundays": "07:00 AM - 07:00 PM",
            "holidays": "08:00 AM - 05:00 PM"
        }
    }'::jsonb),
    ('homepage', '{
        "hero_headline": "TRAIN HARD. STAY STRONG. OWN YOUR PROGRESS.",
        "hero_subheadline": "Train with purpose, build strength and track your fitness journey with a gym experience designed around your goals.",
        "hero_video_url": "/static/videos/hero-fitness.mp4",
        "hero_poster_url": "/static/videos/hero-fitness-poster.jpg"
    }'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- Initial Services
INSERT INTO public.services (name, slug, category, description, image_url, benefits, is_published, sort_order)
VALUES
    ('Strength & Powerlifting', 'strength-training', 'Strength', 'State-of-the-art Olympic barbells, calibrated plates and power cages for serious lifters.', '/static/images/programmes/strength-base.jpg', '["Olympic lifting platforms", "Competition spec barbells", "Form critique by accredited coaches"]'::jsonb, true, 1),
    ('High-Intensity Conditioning', 'conditioning', 'Cardio & HIIT', 'Metabolic conditioning, assault bikes, rowers and battle ropes to shatter endurance limits.', '/static/images/programmes/conditioning.jpg', '["Fat loss & VO2 max building", "Heart rate zone monitoring", "High energy group dynamics"]'::jsonb, true, 2),
    ('Personal Training & Coaching', 'personal-training', 'Coaching', 'Dedicated 1-on-1 athletic coaching tailored to your body composition and functional goals.', '/static/images/programmes/personal-training.jpg', '["Custom progressive overload plans", "Nutritional lifestyle guidance", "Bi-weekly body composition analysis"]'::jsonb, true, 3),
    ('Mobility & Injury Prevention', 'mobility', 'Recovery', 'Functional movement routines, foam rolling, and joint mobility flows to stay supple and pain-free.', '/static/images/programmes/mobility.jpg', '["Deep tissue mobility work", "Active recovery sessions", "Posture restoration protocols"]'::jsonb, true, 4)
ON CONFLICT (slug) DO NOTHING;

-- Initial Membership Plans
INSERT INTO public.membership_plans (name, description, duration_type, duration_days, price, benefits, is_active, is_featured)
VALUES
    ('Daily Pass', 'Full single-day facility access for drop-in athletes and visitors.', 'daily', 1, 500.00, '["Full facility access for 1 day", "Locker & shower facilities", "Free water hydration station"]'::jsonb, true, false),
    ('Monthly Basic', 'Complete 30-day unrestricted gym floor access with self-guided workout tracking.', 'monthly', 30, 4500.00, '["Unlimited gym floor access", "Free weights & cardio zone", "Access to Member Portal & workout logs", "Community Hub participation"]'::jsonb, true, false),
    ('Monthly Pro (Coached)', 'Includes assigned personal trainer, bespoke workout plans and progress reviews.', 'monthly', 30, 9500.00, '["All Basic Plan benefits", "Dedicated certified trainer assigned", "Custom workout plan builder & updates", "Scheduled 1-on-1 coaching sessions", "Bi-weekly progress & measurement reviews"]'::jsonb, true, true),
    ('Quarterly Champion', '90 days of high-performance training with complimentary class passes.', 'quarterly', 90, 12500.00, '["90 days unlimited access", "Priority booking for all group classes", "Full progress tracking analytics", "10% discount on guest day passes"]'::jsonb, true, false),
    ('Annual VIP Athlete', 'Full year elite membership for dedicated gym enthusiasts.', 'annual', 365, 45000.00, '["365 days VIP access", "Full trainer coaching features included", "Free gym locker reservation", "All group classes included"]'::jsonb, true, false)
ON CONFLICT DO NOTHING;

-- Initial Exercise Library
INSERT INTO public.exercise_library (name, category, target_muscle_group, difficulty, equipment_required, instructions, image_url, is_active)
VALUES
    ('Conventional Barbell Deadlift', 'Strength', 'Posterior Chain (Glutes, Hamstrings, Lower Back)', 'Intermediate', 'Olympic Barbell & Bumper Plates', 'Stand with feet hip-width apart. Hinge at hips, grip bar outside knees. Keep spine neutral, chest up, and drive floor away.', '/static/images/exercises/barbell-deadlift.jpg', true),
    ('Barbell Bench Press', 'Strength', 'Chest, Triceps, Anterior Deltoids', 'Intermediate', 'Flat Bench & Olympic Barbell', 'Lie flat on bench, retract scapulae, plant feet. Lower bar with control to mid-chest, press upward locking elbows smoothly.', '/static/images/exercises/barbell-bench-press.jpg', true),
    ('Barbell Back Squat', 'Strength', 'Quadriceps, Glutes, Core', 'Intermediate', 'Power Rack & Barbell', 'Rest barbell across upper traps. Break at hips and knees simultaneously. Descend below parallel, drive up through midfoot.', '/static/images/exercises/barbell-squat.jpg', true),
    ('Strict Pull-Ups', 'Bodyweight', 'Lats, Rhomboids, Biceps', 'Intermediate', 'Pull-Up Bar', 'Hang from bar with overhand grip wider than shoulders. Pull chest to bar while depressing shoulders. Lower under control.', '/static/images/exercises/pull-ups.jpg', true),
    ('Seated Dumbbell Shoulder Press', 'Strength', 'Deltoids, Upper Chest, Triceps', 'Beginner', 'Adjustable Bench & Dumbbells', 'Sit with back supported. Hold dumbbells at shoulder level with elbows angled slightly forward. Press vertically overhead.', '/static/images/exercises/dumbbell-shoulder-press.jpg', true),
    ('Russian Kettlebell Swing', 'Cardio & Power', 'Glutes, Hamstrings, Core', 'Beginner', 'Kettlebell', 'Stand feet shoulder-width. Hinge at hips with soft knees, swing kettlebell back between legs, explode hips forward to chest height.', '/static/images/exercises/kettlebell-swings.jpg', true),
    ('Treadmill Interval Sprints', 'Cardio', 'Cardiovascular System & Legs', 'Intermediate', 'Curved or Motorized Treadmill', 'Warm up for 3 mins. Alternate 30 seconds max effort sprint with 60 seconds walking recovery for 8-10 rounds.', '/static/images/exercises/treadmill-interval.jpg', true),
    ('Forearm Plank Hold', 'Core', 'Transverse Abdominis & Core', 'Beginner', 'Exercise Mat', 'Rest on forearms and toes. Keep body in a straight line from head to heels. Squeeze glutes and brace core for duration.', '/static/images/exercises/plank-hold.jpg', true)
ON CONFLICT DO NOTHING;

-- Initial Gym Equipment
INSERT INTO public.gym_equipment (name, category, model_serial, acquisition_date, condition, is_available, image_url, location, notes)
VALUES
    ('Eleiko Olympic Competition Barbell 20kg', 'Free Weights', 'ELK-OB-2024-01', '2024-01-15', 'excellent', true, '/static/images/equipment/olympic-barbells.jpg', 'Platform Zone A', 'Calibrated to IWF specifications.'),
    ('Commercial Rubber Hex Dumbbell Set (2.5kg - 50kg)', 'Free Weights', 'RH-DB-SET-01', '2024-02-01', 'excellent', true, '/static/images/equipment/dumbbells-rack.jpg', 'Main Free Weights Floor', 'Full dual tier rack with pairs from 2.5kg to 50kg.'),
    ('Heavy-Duty Commercial Power Cage', 'Racks', 'PC-HD-900', '2024-01-20', 'excellent', true, '/static/images/equipment/power-cage.jpg', 'Squat Zone 1', 'Includes safety spotter pins, pull-up bar, and dip handles.'),
    ('Woodway Curve Non-Motorized Treadmill', 'Cardio', 'WW-CRV-102', '2024-03-10', 'excellent', true, '/static/images/equipment/curved-treadmill.jpg', 'Cardio Loft', 'Self-propelled high-speed interval running deck.'),
    ('Dual Adjustable Cable Crossover Station', 'Cable Machines', 'CAB-DACC-04', '2024-01-25', 'good', true, '/static/images/equipment/cable-crossover.jpg', 'Machine Zone B', 'Dual 100kg weight stacks with multi-angle pulleys.'),
    ('Rogue Echo Air Resistance Bike', 'Conditioning', 'ROG-EB-08', '2024-04-05', 'excellent', true, '/static/images/equipment/air-bike.jpg', 'HIIT Zone', 'Heavy gauge steel fan bike for high-intensity intervals.')
ON CONFLICT DO NOTHING;

-- Initial Community Groups
INSERT INTO public.community_groups (name, slug, description, cover_image, is_active)
VALUES
    ('General Gym Community', 'general-community', 'The main hangout for all Levy Kirinya members, trainers and staff.', '/static/images/homepage/facility-1.jpg', true),
    ('Iron & Heavy Lifting', 'iron-lifting', 'Form checks, PR celebrations, powerlifting discussions, and barbell technique.', '/static/images/programmes/strength-base.jpg', true),
    ('Conditioning & Endurance', 'conditioning-hiit', 'Cardio tips, race training, HIIT workouts, and stamina building strategies.', '/static/images/programmes/conditioning.jpg', true),
    ('Healthy Nutrition & Recovery', 'nutrition-recovery', 'Pre-workout meals, protein recipes, sleep optimisation and active recovery tips.', '/static/images/programmes/mobility.jpg', true)
ON CONFLICT (slug) DO NOTHING;

-- ============================================================================
-- END OF SETUP SCRIPT
-- ============================================================================
