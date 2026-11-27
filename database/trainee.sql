-- ==============================================================================
-- STRAKLY GYM MANAGEMENT SYSTEM — TRAINEE PORTAL MIGRATION
-- Migration: database/trainee.sql
-- ==============================================================================

-- 1. Membership Requests (Upgrades, Renewals, Downgrades, Freezes, Cancellations)
CREATE TABLE IF NOT EXISTS public.membership_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    request_type VARCHAR(50) NOT NULL CHECK (request_type IN ('renewal', 'upgrade', 'downgrade', 'freeze', 'cancellation')),
    target_plan_id UUID REFERENCES public.membership_plans(id) ON DELETE SET NULL,
    current_subscription_id UUID REFERENCES public.member_subscriptions(id) ON DELETE SET NULL,
    reason TEXT,
    freeze_start_date DATE,
    freeze_end_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'processed')),
    admin_notes TEXT,
    reviewed_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. PT Session Wallet (Tracks available prepaid 1-on-1 sessions)
CREATE TABLE IF NOT EXISTS public.member_pt_wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL UNIQUE REFERENCES public.profiles(id) ON DELETE CASCADE,
    total_sessions_purchased INT NOT NULL DEFAULT 0,
    sessions_used INT NOT NULL DEFAULT 0,
    sessions_remaining INT GENERATED ALWAYS AS (total_sessions_purchased - sessions_used) STORED,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 1-on-1 Personal Training (PT) Sessions
CREATE TABLE IF NOT EXISTS public.pt_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    focus_area VARCHAR(100) DEFAULT 'General Fitness',
    notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'requested' CHECK (status IN ('requested', 'confirmed', 'completed', 'cancelled')),
    cancellation_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Coach Assignment & Change Requests
CREATE TABLE IF NOT EXISTS public.coach_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    preferred_trainer_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    request_type VARCHAR(30) NOT NULL DEFAULT 'assign' CHECK (request_type IN ('assign', 'change', 'remove')),
    fitness_goals TEXT,
    notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'declined')),
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

-- 5. Member Fitness Goals
CREATE TABLE IF NOT EXISTS public.member_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'strength' CHECK (category IN ('strength', 'weight_loss', 'muscle_gain', 'endurance', 'habit', 'other')),
    target_value NUMERIC(10, 2),
    current_value NUMERIC(10, 2) DEFAULT 0,
    start_value NUMERIC(10, 2) DEFAULT 0,
    unit VARCHAR(30) DEFAULT 'kg',
    target_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'achieved', 'abandoned')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Member Personal Records (PRs / Max Lifts)
CREATE TABLE IF NOT EXISTS public.member_personal_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    exercise_name VARCHAR(150) NOT NULL,
    weight_kg NUMERIC(8, 2) NOT NULL,
    reps INT NOT NULL DEFAULT 1,
    estimated_one_rep_max NUMERIC(8, 2),
    achieved_on DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Member Progress Photos (Private)
CREATE TABLE IF NOT EXISTS public.member_progress_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    photo_url TEXT NOT NULL,
    photo_tag VARCHAR(50) DEFAULT 'front' CHECK (photo_tag IN ('front', 'side', 'back', 'other')),
    recorded_weight NUMERIC(6, 2),
    taken_on DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT,
    is_private BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Fitness Challenges
CREATE TABLE IF NOT EXISTS public.fitness_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'general' CHECK (category IN ('endurance', 'strength', 'consistency', 'weight_loss', 'general')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    target_metric VARCHAR(100),
    target_value NUMERIC(10, 2),
    badge_name VARCHAR(100),
    badge_icon VARCHAR(50) DEFAULT 'trophy',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Challenge Participants
CREATE TABLE IF NOT EXISTS public.challenge_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_id UUID NOT NULL REFERENCES public.fitness_challenges(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    current_progress NUMERIC(10, 2) DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'joined' CHECK (status IN ('joined', 'completed', 'dropped')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE(challenge_id, member_id)
);

-- 10. Member Achievements & Badges
CREATE TABLE IF NOT EXISTS public.member_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    badge_icon VARCHAR(50) DEFAULT 'award',
    unlocked_at TIMESTAMPTZ DEFAULT NOW(),
    source_challenge_id UUID REFERENCES public.fitness_challenges(id) ON DELETE SET NULL
);

-- 11. Equipment Borrowing & Reservations (Belts, Bands, Mats, Foam Rollers)
CREATE TABLE IF NOT EXISTS public.equipment_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.gym_equipment(id) ON DELETE CASCADE,
    reservation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_time TIME NOT NULL DEFAULT CURRENT_TIME,
    duration_minutes INT NOT NULL DEFAULT 60,
    status VARCHAR(30) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'returned', 'overdue', 'cancelled')),
    returned_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Strakly Merchandise Store Products
CREATE TABLE IF NOT EXISTS public.store_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'apparel' CHECK (category IN ('apparel', 'gear', 'nutrition', 'accessories')),
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'KES',
    stock_quantity INT NOT NULL DEFAULT 10,
    image_url TEXT,
    available_sizes TEXT[] DEFAULT ARRAY['S', 'M', 'L', 'XL'],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. Store Orders (STRICT CASH ON COLLECTION)
CREATE TABLE IF NOT EXISTS public.store_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(30) NOT NULL UNIQUE,
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES public.store_products(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1,
    selected_size VARCHAR(20),
    unit_price NUMERIC(10, 2) NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL DEFAULT 'cash_on_collection',
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'ready_for_pickup', 'completed', 'cancelled')),
    pickup_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. Gym Service Inquiries
CREATE TABLE IF NOT EXISTS public.service_inquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES public.services(id) ON DELETE CASCADE,
    preferred_date DATE,
    preferred_time TIME,
    notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'contacted', 'scheduled', 'closed')),
    admin_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. Help & Support Tickets
CREATE TABLE IF NOT EXISTS public.support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_number VARCHAR(30) NOT NULL UNIQUE,
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL DEFAULT 'general' CHECK (category IN ('membership', 'payment', 'facility', 'coaching', 'equipment', 'general')),
    subject VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status VARCHAR(30) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    admin_reply TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 16. Member Preferences & Settings
CREATE TABLE IF NOT EXISTS public.member_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL UNIQUE REFERENCES public.profiles(id) ON DELETE CASCADE,
    notify_email BOOLEAN DEFAULT TRUE,
    notify_sms BOOLEAN DEFAULT FALSE,
    notify_class_reminders BOOLEAN DEFAULT TRUE,
    notify_community_replies BOOLEAN DEFAULT TRUE,
    share_progress_with_coach BOOLEAN DEFAULT TRUE,
    public_leaderboard BOOLEAN DEFAULT TRUE,
    preferred_theme VARCHAR(20) DEFAULT 'fitpulse',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- INDEXES FOR PERFORMANCE
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_membership_requests_member ON public.membership_requests(member_id);
CREATE INDEX IF NOT EXISTS idx_pt_sessions_member ON public.pt_sessions(member_id);
CREATE INDEX IF NOT EXISTS idx_pt_sessions_trainer ON public.pt_sessions(trainer_id);
CREATE INDEX IF NOT EXISTS idx_member_goals_member ON public.member_goals(member_id);
CREATE INDEX IF NOT EXISTS idx_member_prs_member ON public.member_personal_records(member_id);
CREATE INDEX IF NOT EXISTS idx_store_orders_member ON public.store_orders(member_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_member ON public.support_tickets(member_id);

-- ==============================================================================
-- SEED ESSENTIAL CATALOG & SAMPLE DATA (IF EMPTY)
-- ==============================================================================
INSERT INTO public.fitness_challenges (title, description, category, start_date, end_date, target_metric, target_value, badge_name, badge_icon)
VALUES
    ('30-Day Consistency Streak', 'Check into Strakly Gym at least 20 days this month to establish rock-solid workout discipline.', 'consistency', CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', 'Check-ins', 20, 'Iron Will', 'flame'),
    ('100km Cardio Assault', 'Clock 100 total kilometers across Strakly treadmills, rowers, and assault bikes.', 'endurance', CURRENT_DATE, CURRENT_DATE + INTERVAL '45 days', 'Kilometers', 100, 'Century Rider', 'activity'),
    ('Heavy Lifters 1000lb Club', 'Reach a cumulative 1,000 lbs across your Squat, Bench Press, and Deadlift one-rep maxes.', 'strength', CURRENT_DATE, CURRENT_DATE + INTERVAL '90 days', 'Pounds Lifted', 1000, 'Titan Lifter', 'award')
ON CONFLICT DO NOTHING;

INSERT INTO public.store_products (name, category, description, price, currency, stock_quantity, image_url, available_sizes)
VALUES
    ('Strakly Pro Performance Tee', 'apparel', 'Ultra-breathable sweat-wicking training tee featuring bold Strakly typography on the chest.', 2500, 'KES', 35, 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=800', ARRAY['S', 'M', 'L', 'XL', 'XXL']),
    ('Strakly Heavy Duty Lifting Belt', 'gear', '10mm genuine leather competition lever belt for maximum intra-abdominal pressure and lumbar safety.', 6500, 'KES', 12, 'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?w=800', ARRAY['M', 'L', 'XL']),
    ('Strakly Stainless Steel Shaker (750ml)', 'accessories', 'Double-wall vacuum insulated matte black shaker bottle with leak-proof screw cap.', 1800, 'KES', 50, 'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=800', ARRAY['Standard']),
    ('Strakly Elite Gym Duffle Bag', 'gear', 'Waterproof gym duffle bag with isolated ventilated sneaker compartment and wet pouch.', 4200, 'KES', 20, 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800', ARRAY['Standard'])
ON CONFLICT DO NOTHING;
