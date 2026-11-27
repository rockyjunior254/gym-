-- ==============================================================================
-- STRAKLY GYM MANAGEMENT SYSTEM — COMPLETE TRAINER PORTAL & PUBLIC WEBSITE SQL
-- Migration: database/trainer.sql
-- ==============================================================================
-- Comprehensive, safe, idempotent database migration for the Trainer Portal,
-- public coach profiles, scheduling, assessments, athlete check-ins, and
-- trainer-proposed specialized coaching programmes.
-- ==============================================================================

-- 1. EXTEND TRAINER DETAILS FOR PUBLIC PROFILE APPROVAL WORKFLOW
DO $$
BEGIN
    -- Trainer Identification Number (if not already created)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'trainer_number') THEN
        ALTER TABLE public.trainer_details ADD COLUMN trainer_number TEXT;
    END IF;

    -- Hourly Rate & Active Status
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'hourly_rate') THEN
        ALTER TABLE public.trainer_details ADD COLUMN hourly_rate NUMERIC(10, 2) DEFAULT 3500.00;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'is_active') THEN
        ALTER TABLE public.trainer_details ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;

    -- Certifications & Accreditations (e.g. CSCS, NASM, FMS)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'certifications') THEN
        ALTER TABLE public.trainer_details ADD COLUMN certifications TEXT;
    END IF;

    -- Coaching Philosophy & Approach
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'coaching_philosophy') THEN
        ALTER TABLE public.trainer_details ADD COLUMN coaching_philosophy TEXT;
    END IF;

    -- Experience in Years
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'experience_years') THEN
        ALTER TABLE public.trainer_details ADD COLUMN experience_years INT DEFAULT 3;
    END IF;

    -- Public Profile Publication & Approval State
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'profile_status') THEN
        ALTER TABLE public.trainer_details ADD COLUMN profile_status VARCHAR(30) DEFAULT 'approved';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'is_published') THEN
        ALTER TABLE public.trainer_details ADD COLUMN is_published BOOLEAN DEFAULT TRUE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'rejection_reason') THEN
        ALTER TABLE public.trainer_details ADD COLUMN rejection_reason TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'submitted_at') THEN
        ALTER TABLE public.trainer_details ADD COLUMN submitted_at TIMESTAMPTZ DEFAULT NOW();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'approved_at') THEN
        ALTER TABLE public.trainer_details ADD COLUMN approved_at TIMESTAMPTZ DEFAULT NOW();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'approved_by') THEN
        ALTER TABLE public.trainer_details ADD COLUMN approved_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'social_links') THEN
        ALTER TABLE public.trainer_details ADD COLUMN social_links JSONB DEFAULT '{}'::jsonb;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'rating') THEN
        ALTER TABLE public.trainer_details ADD COLUMN rating NUMERIC(3, 2) DEFAULT 4.95;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trainer_details' AND column_name = 'review_count') THEN
        ALTER TABLE public.trainer_details ADD COLUMN review_count INT DEFAULT 18;
    END IF;

    -- Ensure trainer_assignments.assigned_by is nullable to support flexible coach assignments
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trainer_assignments' AND column_name = 'assigned_by' AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE public.trainer_assignments ALTER COLUMN assigned_by DROP NOT NULL;
    END IF;

    -- Ensure pt_sessions has duration_minutes if previously created without it
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pt_sessions') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pt_sessions' AND column_name = 'duration_minutes') THEN
            ALTER TABLE public.pt_sessions ADD COLUMN duration_minutes INT DEFAULT 60;
        END IF;
    END IF;
END $$;

-- 2. TRAINER AVAILABILITY & WEEKLY WORKING HOURS
CREATE TABLE IF NOT EXISTS public.trainer_availability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    day_of_week VARCHAR(20) NOT NULL CHECK (day_of_week IN ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')),
    start_time TIME NOT NULL DEFAULT '06:00',
    end_time TIME NOT NULL DEFAULT '20:00',
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trainer_avail_trainer ON public.trainer_availability(trainer_id);
CREATE INDEX IF NOT EXISTS idx_trainer_avail_day ON public.trainer_availability(day_of_week);

-- 3. FITNESS ASSESSMENTS & PERFORMANCE EVALUATIONS
CREATE TABLE IF NOT EXISTS public.fitness_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    fitness_objectives TEXT,
    general_observations TEXT,
    strength_observations TEXT,
    endurance_observations TEXT,
    mobility_observations TEXT,
    measurements JSONB DEFAULT '{}'::jsonb,
    recommendations TEXT,
    next_review_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fitness_assess_member ON public.fitness_assessments(member_id);
CREATE INDEX IF NOT EXISTS idx_fitness_assess_trainer ON public.fitness_assessments(trainer_id);
CREATE INDEX IF NOT EXISTS idx_fitness_assess_date ON public.fitness_assessments(assessment_date DESC);

-- 4. ATHLETE CHECK-INS & COACH FEEDBACK
CREATE TABLE IF NOT EXISTS public.athlete_checkins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    checkin_date DATE NOT NULL DEFAULT CURRENT_DATE,
    energy_rating INTEGER CHECK (energy_rating BETWEEN 1 AND 5),
    soreness_rating INTEGER CHECK (soreness_rating BETWEEN 1 AND 5),
    nutrition_adherence VARCHAR(50) DEFAULT 'On Track',
    athlete_notes TEXT,
    trainer_feedback TEXT,
    feedback_date TIMESTAMPTZ,
    status VARCHAR(30) DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_checkins_member ON public.athlete_checkins(member_id);
CREATE INDEX IF NOT EXISTS idx_checkins_trainer ON public.athlete_checkins(trainer_id);
CREATE INDEX IF NOT EXISTS idx_checkins_status ON public.athlete_checkins(status);

-- 5. TRAINER-PROPOSED SPECIALISED PROGRAMMES (Part 5 Requirements)
CREATE TABLE IF NOT EXISTS public.trainer_programmes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    objective VARCHAR(150),
    duration_weeks INTEGER DEFAULT 6,
    sessions_count INTEGER DEFAULT 18,
    target_audience VARCHAR(100) DEFAULT 'Intermediate / Advanced',
    category VARCHAR(100) DEFAULT 'Strength & Conditioning',
    proposed_price NUMERIC(10, 2) DEFAULT 12000,
    status VARCHAR(30) DEFAULT 'approved' CHECK (status IN ('draft', 'pending', 'approved', 'rejected')),
    is_published BOOLEAN DEFAULT TRUE,
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trainer_prog_trainer ON public.trainer_programmes(trainer_id);
CREATE INDEX IF NOT EXISTS idx_trainer_prog_status ON public.trainer_programmes(status);
CREATE INDEX IF NOT EXISTS idx_trainer_prog_published ON public.trainer_programmes(is_published);

-- 6. ENSURE 1-ON-1 COACHING SESSIONS (PT SESSIONS)
CREATE TABLE IF NOT EXISTS public.pt_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    duration_minutes INT DEFAULT 60,
    focus_area VARCHAR(100) DEFAULT 'Strength & Hypertrophy',
    notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('requested', 'confirmed', 'completed', 'cancelled')),
    cancellation_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pt_sessions_member ON public.pt_sessions(member_id);
CREATE INDEX IF NOT EXISTS idx_pt_sessions_trainer ON public.pt_sessions(trainer_id);
CREATE INDEX IF NOT EXISTS idx_pt_sessions_date ON public.pt_sessions(session_date DESC);

-- 7. ENSURE WORKOUT PLANS AND EXERCISES
CREATE TABLE IF NOT EXISTS public.workout_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    title VARCHAR(150) NOT NULL,
    goal VARCHAR(100),
    days_per_week INT DEFAULT 4,
    status VARCHAR(30) DEFAULT 'active' CHECK (status IN ('active', 'draft', 'archived')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.workout_plan_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES public.workout_plans(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES public.exercise_library(id) ON DELETE SET NULL,
    day_number INT DEFAULT 1,
    sets INT DEFAULT 3,
    reps INT DEFAULT 10,
    rest_seconds INT DEFAULT 90,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. PUBLIC MEMBER TESTIMONIALS & ATHLETE STORIES (Part 6.9)
CREATE TABLE IF NOT EXISTS public.member_testimonials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    trainer_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    author_name VARCHAR(150) NOT NULL,
    author_title VARCHAR(100) DEFAULT 'Competitive Powerlifter',
    quote TEXT NOT NULL,
    transformation_stat VARCHAR(100) DEFAULT '+45kg Squat PR',
    rating INT DEFAULT 5,
    avatar_url TEXT,
    is_featured BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. ENABLE ROW LEVEL SECURITY (RLS)
ALTER TABLE public.trainer_availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fitness_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.athlete_checkins ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trainer_programmes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pt_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_testimonials ENABLE ROW LEVEL SECURITY;

-- 10. RLS POLICIES
-- Availability: Trainer can manage own, Admin can manage all, Public can read active
DROP POLICY IF EXISTS trainer_avail_all ON public.trainer_availability;
CREATE POLICY trainer_avail_all ON public.trainer_availability
    FOR ALL USING (trainer_id = auth.uid() OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

DROP POLICY IF EXISTS trainer_avail_public_read ON public.trainer_availability;
CREATE POLICY trainer_avail_public_read ON public.trainer_availability
    FOR SELECT USING (is_available = TRUE);

-- Assessments: Only authorized trainer, athlete, or admin
DROP POLICY IF EXISTS fitness_assess_authorized ON public.fitness_assessments;
CREATE POLICY fitness_assess_authorized ON public.fitness_assessments
    FOR ALL USING (
        trainer_id = auth.uid() 
        OR member_id = auth.uid() 
        OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
    );

-- Check-ins: Only assigned trainer, athlete, or admin
DROP POLICY IF EXISTS athlete_checkins_authorized ON public.athlete_checkins;
CREATE POLICY athlete_checkins_authorized ON public.athlete_checkins
    FOR ALL USING (
        trainer_id = auth.uid() 
        OR member_id = auth.uid() 
        OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
    );

-- Trainer Programmes: Trainer manages own, Admin manages all, Public reads approved/published
DROP POLICY IF EXISTS trainer_prog_trainer_all ON public.trainer_programmes;
CREATE POLICY trainer_prog_trainer_all ON public.trainer_programmes
    FOR ALL USING (
        trainer_id = auth.uid() 
        OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
    );

DROP POLICY IF EXISTS trainer_prog_public_read ON public.trainer_programmes;
CREATE POLICY trainer_prog_public_read ON public.trainer_programmes
    FOR SELECT USING (status = 'approved' AND is_published = TRUE);

-- PT Sessions: Trainer, Member, or Admin
DROP POLICY IF EXISTS pt_sessions_authorized ON public.pt_sessions;
CREATE POLICY pt_sessions_authorized ON public.pt_sessions
    FOR ALL USING (
        trainer_id = auth.uid() 
        OR member_id = auth.uid() 
        OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
    );

-- Member Testimonials: Public read, Admin manage
DROP POLICY IF EXISTS member_testimonials_public ON public.member_testimonials;
CREATE POLICY member_testimonials_public ON public.member_testimonials
    FOR SELECT USING (is_featured = TRUE);

DROP POLICY IF EXISTS member_testimonials_admin ON public.member_testimonials;
CREATE POLICY member_testimonials_admin ON public.member_testimonials
    FOR ALL USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'));

-- ==============================================================================
-- 11. RICH SEED DATA (For Immediate Full Functionality in Supabase)
-- ==============================================================================

-- A. Insert/Update Core Trainer Profiles if they exist or create demo coaches
DO $$
DECLARE
    v_trainer1_id UUID;
    v_trainer2_id UUID;
    v_trainer3_id UUID;
    v_trainer4_id UUID;
    v_member1_id UUID;
    v_member2_id UUID;
    v_admin_id UUID;
BEGIN
    -- Look for existing trainer profiles
    SELECT id INTO v_trainer1_id FROM public.profiles WHERE role = 'trainer' ORDER BY created_at ASC LIMIT 1;
    SELECT id INTO v_member1_id FROM public.profiles WHERE role = 'member' ORDER BY created_at ASC LIMIT 1;
    SELECT id INTO v_member2_id FROM public.profiles WHERE role = 'member' ORDER BY created_at DESC LIMIT 1;
    SELECT id INTO v_admin_id FROM public.profiles WHERE role = 'admin' ORDER BY created_at ASC LIMIT 1;

    -- If no trainer exists, generate deterministic IDs for testing/demo
    IF v_trainer1_id IS NULL THEN
        v_trainer1_id := 'd0000000-0000-0000-0000-000000000002'::uuid;
        INSERT INTO public.profiles (id, email, full_name, phone, role, avatar_url)
        VALUES (v_trainer1_id, 'coach.james@strakly.local', 'Coach James Scott', '+254 700 112 233', 'trainer', '/static/images/trainers/trainer-1.jpg')
        ON CONFLICT (id) DO UPDATE SET full_name = 'Coach James Scott', role = 'trainer';
    END IF;

    -- Upsert Trainer Details with rich credentials
    INSERT INTO public.trainer_details (
        id, trainer_number, bio, specialisations, hourly_rate, is_active,
        certifications, coaching_philosophy, experience_years,
        profile_status, is_published, rating, review_count
    ) VALUES (
        v_trainer1_id,
        'STK-TR-001',
        'Head Strength & Conditioning Coach with 8+ years specializing in competitive powerlifting, kinetic bar speed analysis, and injury-resilient biomechanics.',
        ARRAY['Powerlifting', 'Strength & Conditioning', 'Barbell Mechanics', 'Hypertrophy'],
        3500.00,
        TRUE,
        'CSCS (Certified Strength & Conditioning Specialist), USAW Level 2 Weightlifting Coach',
        'Consistency and strict technical execution surpass raw intensity. We engineer lasting strength without compromise.',
        8,
        'approved',
        TRUE,
        4.98,
        24
    ) ON CONFLICT (id) DO UPDATE SET
        trainer_number = COALESCE(trainer_details.trainer_number, 'STK-TR-001'),
        hourly_rate = 3500.00,
        is_active = TRUE,
        certifications = EXCLUDED.certifications,
        coaching_philosophy = EXCLUDED.coaching_philosophy,
        experience_years = EXCLUDED.experience_years,
        profile_status = 'approved',
        is_published = TRUE,
        rating = 4.98,
        review_count = 24;

    -- Upsert Trainer Availability (Mon - Sat)
    INSERT INTO public.trainer_availability (trainer_id, day_of_week, start_time, end_time, is_available, notes)
    VALUES
        (v_trainer1_id, 'monday', '06:00', '19:00', TRUE, 'Morning Powerlifting blocks & 1-on-1 coaching'),
        (v_trainer1_id, 'tuesday', '06:00', '19:00', TRUE, 'Strength fundamentals & Athlete assessments'),
        (v_trainer1_id, 'wednesday', '06:00', '19:00', TRUE, 'Hypertrophy volume & Check-in reviews'),
        (v_trainer1_id, 'thursday', '06:00', '19:00', TRUE, 'Olympic lifting technique drills'),
        (v_trainer1_id, 'friday', '06:00', '18:00', TRUE, 'Heavy deadlift prep & mobility work'),
        (v_trainer1_id, 'saturday', '08:00', '14:00', TRUE, 'Weekend athletic conditioning clinics')
    ON CONFLICT DO NOTHING;

    -- Ensure v_admin_id fallback if no admin user exists
    IF v_admin_id IS NULL THEN
        v_admin_id := v_trainer1_id;
    END IF;

    -- If a member exists, connect athlete assignment, sessions, assessment, and check-in
    IF v_member1_id IS NOT NULL THEN
        -- Assignment with explicit assigned_by
        INSERT INTO public.trainer_assignments (trainer_id, member_id, status, assigned_by, notes)
        VALUES (v_trainer1_id, v_member1_id, 'active', v_admin_id, 'Assigned for national powerlifting prep')
        ON CONFLICT DO NOTHING;

        -- Scheduled 1-on-1 Session
        INSERT INTO public.pt_sessions (member_id, trainer_id, session_date, start_time, duration_minutes, focus_area, notes, status)
        VALUES
            (v_member1_id, v_trainer1_id, CURRENT_DATE + INTERVAL '1 day', '09:00', 60, 'Heavy Squat Form & Knee Tracking', 'Review pause squat depth and bar speed', 'confirmed'),
            (v_member1_id, v_trainer1_id, CURRENT_DATE - INTERVAL '2 days', '10:00', 60, 'Deadlift Lockout & Lat Engagement', 'Hit new 5-rep technical PR', 'completed')
        ON CONFLICT DO NOTHING;

        -- Fitness Assessment
        INSERT INTO public.fitness_assessments (
            member_id, trainer_id, assessment_date,
            fitness_objectives, general_observations, strength_observations,
            endurance_observations, mobility_observations, recommendations, next_review_date,
            measurements
        ) VALUES (
            v_member1_id, v_trainer1_id, CURRENT_DATE - INTERVAL '14 days',
            'Increase squat 1RM to 180kg, improve hip mobility, and optimize body composition.',
            'Athlete demonstrates excellent discipline, core bracing, and training adherence.',
            'Bench press 110kg (clean pause), Back Squat 165kg, Conventional Deadlift 205kg.',
            'High recovery rate between working sets; resting heart rate at 54 bpm.',
            'Slight restriction in thoracic extension and right ankle dorsiflexion.',
            'Incorporate 10-minute ankle banded mobilization prior to heavy squats. Progress volume by 3% weekly.',
            CURRENT_DATE + INTERVAL '16 days',
            '{"weight_kg": 82.5, "body_fat_pct": 13.8, "chest_cm": 104, "waist_cm": 81, "arms_cm": 39}'::jsonb
        ) ON CONFLICT DO NOTHING;

        -- Athlete Check-in
        INSERT INTO public.athlete_checkins (
            member_id, trainer_id, checkin_date,
            energy_rating, soreness_rating, nutrition_adherence,
            athlete_notes, trainer_feedback, feedback_date, status
        ) VALUES
            (v_member1_id, v_trainer1_id, CURRENT_DATE, 5, 2, '100% on target', 'Felt very explosive on the bench press today. Sleep was 8.5 hours.', 'Outstanding work on the pause reps. Keep protein intake consistent ahead of Thursday volume.', NOW(), 'reviewed'),
            (v_member1_id, v_trainer1_id, CURRENT_DATE - INTERVAL '3 days', 4, 3, 'Mostly on track', 'Slight hamstring tightness after deadlifts.', 'Add 3 sets of seated hamstring curls with slow eccentric tempo to alleviate tension.', NOW() - INTERVAL '2 days', 'reviewed')
        ON CONFLICT DO NOTHING;

        -- Active Workout Plan
        INSERT INTO public.workout_plans (member_id, trainer_id, title, goal, days_per_week, status, notes)
        VALUES (v_member1_id, v_trainer1_id, 'Elite Barbell Hypertrophy & Peak Strength', 'Strength & Hypertrophy', 4, 'active', 'Block 2: Progressive overload with RPE 8-9 targets.')
        ON CONFLICT DO NOTHING;
    END IF;

    -- Seed Trainer-Proposed Programmes (Part 5)
    INSERT INTO public.trainer_programmes (
        trainer_id, name, description, objective,
        duration_weeks, sessions_count, target_audience, category,
        proposed_price, status, is_published, admin_notes
    ) VALUES (
        v_trainer1_id,
        'Iron Powerlifting Mastery Protocol',
        'A comprehensive 8-week periodized coaching programme designed for lifters looking to add 20kg–40kg to their competition total through kinetic velocity tracking and technique mastery.',
        'Max Strength & Competition Peaking',
        8,
        24,
        'Intermediate to Advanced Barbell Athletes',
        'Powerlifting & Strength',
        18000.00,
        'approved',
        TRUE,
        'Approved by Head of Athletics. Published to public website catalog.'
    ), (
        v_trainer1_id,
        'Barbell Hypertrophy & Athletic Foundation',
        '6-week muscle volume and joint resilience cycle focusing on high-tension compound movements, structural balance, and metabolic conditioning.',
        'Hypertrophy & Joint Longevity',
        6,
        18,
        'All Experience Levels',
        'Strength & Conditioning',
        12500.00,
        'approved',
        TRUE,
        'Verified and published.'
    ) ON CONFLICT DO NOTHING;

    -- Seed Public Member Testimonials (Part 6.9)
    INSERT INTO public.member_testimonials (
        author_name, author_title, quote, transformation_stat, rating, avatar_url, is_featured
    ) VALUES
        ('Marcus Kiprop', 'Powerlifting Athlete', 'Training under Coach James Scott completely rebuilt my squat mechanics. The physical check-ins and disciplined programming took my total from 480kg to 545kg in 6 months.', '+65kg Competition Total', 5, '/static/images/placeholders/avatar-default.svg', TRUE),
        ('Brenda Wanjiku', 'Marathon & Strength Competitor', 'Strakly is unlike any ordinary gym in Nairobi. The coaches treat your programming like elite athletic preparation. Transparent cash receipts and structured sessions keep everything professional.', '+12% Metabolic Stamina', 5, '/static/images/placeholders/avatar-default.svg', TRUE),
        ('David Otieno', 'Strength & Hypertrophy Trainee', 'The trainer portal integration makes coaching seamless. My coach reviews my check-ins and updates my weekly barbell volume directly in the platform.', '-6.5% Body Fat / +8kg Lean Mass', 5, '/static/images/placeholders/avatar-default.svg', TRUE)
    ON CONFLICT DO NOTHING;

END $$;

-- Verification summary output
SELECT 'Trainer Portal database schema and seed data successfully initialized.' AS status;
