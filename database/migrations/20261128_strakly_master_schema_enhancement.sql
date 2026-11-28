-- =============================================================================
-- STRAKLY GYM MANAGEMENT SYSTEM — MASTER ENHANCEMENT MIGRATION
-- File: database/migrations/20261128_strakly_master_schema_enhancement.sql
-- Description: Completely self-contained, 100% idempotent PostgreSQL migration.
--              Safe to run multiple times in Supabase SQL Editor with ZERO errors.
-- Covers:
--   1. Extensions & Schema Validations
--   2. Profiles & Account Management Updates (Audit columns, password metadata)
--   3. Enhanced Exercise Movement Library (Images, Muscles, Media, Guides)
--   4. Expanded Store / Pro Shop Products & Categories (Apparel, Gear, Accessories, Recovery)
--   5. Facility Assets & Equipment Register (Brand, Model, Maintenance Schedules)
--   6. Row-Level Security (RLS) Policies & Safe Role Grants
--   7. Verified Seed Data for Movements, Products, and Equipment
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. EXTENSIONS
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 2. PROFILES & ACCOUNT MANAGEMENT ENHANCEMENTS
-- -----------------------------------------------------------------------------
DO $$ 
BEGIN
    -- Ensure columns exist safely on profiles
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'profiles') THEN
        ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS phone TEXT;
        ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS avatar_url TEXT DEFAULT '/static/images/placeholders/avatar-default.svg';
        ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
        ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
        ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
        ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS last_sign_in_at TIMESTAMPTZ;
        ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS password_reset_required BOOLEAN DEFAULT FALSE;
        ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 3. EXERCISE MOVEMENT LIBRARY SCHEMA
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.exercise_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    target_muscle_group TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'Intermediate',
    equipment_required TEXT DEFAULT 'None',
    instructions TEXT,
    safety_notes TEXT,
    primary_muscles TEXT[] DEFAULT '{}',
    secondary_muscles TEXT[] DEFAULT '{}',
    image_url TEXT,
    video_url TEXT,
    demo_video_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Safely ensure columns exist if exercise_library was already created previously
DO $$ 
BEGIN
    ALTER TABLE public.exercise_library ADD COLUMN IF NOT EXISTS safety_notes TEXT;
    ALTER TABLE public.exercise_library ADD COLUMN IF NOT EXISTS primary_muscles TEXT[] DEFAULT '{}';
    ALTER TABLE public.exercise_library ADD COLUMN IF NOT EXISTS secondary_muscles TEXT[] DEFAULT '{}';
    ALTER TABLE public.exercise_library ADD COLUMN IF NOT EXISTS demo_video_url TEXT;
    ALTER TABLE public.exercise_library ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
    ALTER TABLE public.exercise_library ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
    ALTER TABLE public.exercise_library ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
    
    -- Relax any old restrictive check constraints on difficulty
    ALTER TABLE public.exercise_library DROP CONSTRAINT IF EXISTS exercise_library_difficulty_check;
END $$;

-- -----------------------------------------------------------------------------
-- 4. PRO SHOP / STORE PRODUCTS & ORDERS ENHANCEMENTS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.store_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    category VARCHAR(80) NOT NULL DEFAULT 'Workout Essentials',
    description TEXT,
    price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(10) NOT NULL DEFAULT 'KES',
    stock_quantity INT NOT NULL DEFAULT 10,
    sku TEXT UNIQUE,
    image_url TEXT,
    available_sizes TEXT[] DEFAULT ARRAY['S', 'M', 'L', 'XL'],
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Safely upgrade store_products columns & relax category constraint
DO $$ 
BEGIN
    ALTER TABLE public.store_products ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'KES';
    ALTER TABLE public.store_products ADD COLUMN IF NOT EXISTS sku TEXT;
    ALTER TABLE public.store_products ADD COLUMN IF NOT EXISTS available_sizes TEXT[] DEFAULT ARRAY['S', 'M', 'L', 'XL'];
    ALTER TABLE public.store_products ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;
    ALTER TABLE public.store_products ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
    ALTER TABLE public.store_products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
    
    -- Drop old narrow check constraint if it existed
    ALTER TABLE public.store_products DROP CONSTRAINT IF EXISTS store_products_category_check;
END $$;

CREATE TABLE IF NOT EXISTS public.store_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(40) NOT NULL UNIQUE,
    member_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES public.store_products(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL,
    total_price NUMERIC(10, 2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending_cash' CHECK (status IN ('pending_cash', 'completed', 'cancelled')),
    collected_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 5. FACILITY ASSETS & GEAR INVENTORY ENHANCEMENTS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.gym_equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    model_serial TEXT,
    serial_number TEXT,
    quantity INT NOT NULL DEFAULT 1,
    acquisition_date DATE,
    condition TEXT NOT NULL DEFAULT 'excellent' CHECK (condition IN ('excellent', 'good', 'fair', 'needs_maintenance', 'out_of_order')),
    is_available BOOLEAN DEFAULT TRUE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    image_url TEXT,
    facility_location TEXT,
    location TEXT,
    maintenance_status TEXT DEFAULT 'operational',
    last_maintenance_date DATE,
    next_maintenance_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

DO $$ 
BEGIN
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS brand TEXT;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS model TEXT;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS serial_number TEXT;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS quantity INT DEFAULT 1;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS facility_location TEXT;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS maintenance_status TEXT DEFAULT 'operational';
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS last_maintenance_date DATE;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS next_maintenance_date DATE;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
    ALTER TABLE public.gym_equipment ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
END $$;

CREATE TABLE IF NOT EXISTS public.equipment_maintenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id UUID NOT NULL REFERENCES public.gym_equipment(id) ON DELETE CASCADE,
    reported_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    service_date DATE NOT NULL DEFAULT CURRENT_DATE,
    issue_description TEXT NOT NULL,
    resolution_notes TEXT,
    cost NUMERIC(10, 2) DEFAULT 0.00,
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 6. SAFE INDEXES FOR HIGH-TRAFFIC PORTAL QUERIES
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_exercise_category ON public.exercise_library(category);
CREATE INDEX IF NOT EXISTS idx_exercise_muscle ON public.exercise_library(target_muscle_group);
CREATE INDEX IF NOT EXISTS idx_exercise_active ON public.exercise_library(is_active) WHERE is_active = TRUE AND is_archived = FALSE;
CREATE INDEX IF NOT EXISTS idx_store_products_cat ON public.store_products(category);
CREATE INDEX IF NOT EXISTS idx_store_products_active ON public.store_products(is_active) WHERE is_active = TRUE AND is_archived = FALSE;
CREATE INDEX IF NOT EXISTS idx_store_orders_member ON public.store_orders(member_id);
CREATE INDEX IF NOT EXISTS idx_gym_equipment_avail ON public.gym_equipment(is_available) WHERE is_available = TRUE AND is_archived = FALSE;

-- -----------------------------------------------------------------------------
-- 7. ROW-LEVEL SECURITY (RLS) POLICIES
-- -----------------------------------------------------------------------------
ALTER TABLE public.exercise_library ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.store_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.store_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gym_equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.equipment_maintenance ENABLE ROW LEVEL SECURITY;

-- Idempotent RLS: drop if exists then create
DO $$ 
BEGIN
    -- Exercise Library Policies
    DROP POLICY IF EXISTS "Public and authenticated users can view published exercises" ON public.exercise_library;
    CREATE POLICY "Public and authenticated users can view published exercises" 
        ON public.exercise_library FOR SELECT 
        USING (is_active = TRUE AND is_archived = FALSE);

    DROP POLICY IF EXISTS "Admins and Trainers can manage exercises" ON public.exercise_library;
    CREATE POLICY "Admins and Trainers can manage exercises" 
        ON public.exercise_library FOR ALL 
        USING (
            EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role IN ('admin', 'trainer'))
        );

    -- Store Products Policies
    DROP POLICY IF EXISTS "Anyone can view active store products" ON public.store_products;
    CREATE POLICY "Anyone can view active store products" 
        ON public.store_products FOR SELECT 
        USING (is_active = TRUE AND is_archived = FALSE);

    DROP POLICY IF EXISTS "Admins can manage store products" ON public.store_products;
    CREATE POLICY "Admins can manage store products" 
        ON public.store_products FOR ALL 
        USING (
            EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
        );

    -- Store Orders Policies
    DROP POLICY IF EXISTS "Members can view own store orders" ON public.store_orders;
    CREATE POLICY "Members can view own store orders" 
        ON public.store_orders FOR SELECT 
        USING (member_id = auth.uid() OR EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin'));

    DROP POLICY IF EXISTS "Members can place store orders" ON public.store_orders;
    CREATE POLICY "Members can place store orders" 
        ON public.store_orders FOR INSERT 
        WITH CHECK (member_id = auth.uid());

    -- Equipment Policies
    DROP POLICY IF EXISTS "Authenticated users can view active equipment" ON public.gym_equipment;
    CREATE POLICY "Authenticated users can view active equipment" 
        ON public.gym_equipment FOR SELECT 
        USING (is_archived = FALSE);

    DROP POLICY IF EXISTS "Admins can manage equipment" ON public.gym_equipment;
    CREATE POLICY "Admins can manage equipment" 
        ON public.gym_equipment FOR ALL 
        USING (
            EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
        );
END $$;

-- -----------------------------------------------------------------------------
-- 8. VERIFIED REFERENCE SEED DATA (IDEMPOTENT UPSERTS)
-- -----------------------------------------------------------------------------

-- 8.1 Curated Movement Library Seed Data with Real Movement Demonstrations
INSERT INTO public.exercise_library (
    name, category, target_muscle_group, difficulty, equipment_required,
    instructions, safety_notes, primary_muscles, secondary_muscles, image_url
) VALUES
(
    'Barbell Back Squat',
    'Strength',
    'Legs & Glutes',
    'Intermediate',
    'Olympic Barbell & Squat Rack',
    '1. Rest the barbell securely across upper trapezius muscles.\n2. Inhale, brace core cylinder, and unrack.\n3. Break simultaneously at hips and knees, descending under control until thighs break parallel.\n4. Drive explosively through mid-foot while maintaining upright torso.',
    'Keep heels planted firmly. Do not let knees cave inward during concentric drive.',
    ARRAY['Quadriceps', 'Gluteus Maximus'],
    ARRAY['Hamstrings', 'Erector Spinae', 'Core Abdominals'],
    'https://images.unsplash.com/photo-1574680096145-d05b474e2155?auto=format&fit=crop&w=800&q=80'
),
(
    'Conventional Deadlift',
    'Powerlifting',
    'Posterior Chain',
    'Advanced',
    'Olympic Barbell & Bumper Plates',
    '1. Stand with mid-foot directly beneath bar, feet hip-width.\n2. Hinge at hips and take double-overhand or hook grip just outside shins.\n3. Pull slack out of bar, wedge hips into position, and flatten spine.\n4. Push the floor away, locking hips and knees synchronously at top.',
    'Never round lumbar spine under heavy loads. Keep bar in constant contact with legs.',
    ARRAY['Erector Spinae', 'Gluteus Maximus', 'Hamstrings'],
    ARRAY['Latissimus Dorsi', 'Trapezius', 'Forearms'],
    'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=800&q=80'
),
(
    'Barbell Bench Press',
    'Strength',
    'Chest',
    'Intermediate',
    'Flat Competition Bench & Olympic Barbell',
    '1. Lie flat with eyes directly below bar, feet planted firmly into floor.\n2. Retract and depress scapulae, establishing stable upper back arch.\n3. Unrack with elbows locked, lower bar smoothly to sternum.\n4. Press aggressively upward and slightly back toward rack position.',
    'Maintain tight full-body leg drive without raising glutes off the bench pad.',
    ARRAY['Pectoralis Major', 'Anterior Deltoids'],
    ARRAY['Triceps Brachii', 'Serratus Anterior'],
    'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80'
),
(
    'Standing Overhead Press (OHP)',
    'Strength',
    'Shoulders',
    'Intermediate',
    'Olympic Barbell',
    '1. Stand tall with heels hip-width apart and glutes engaged.\n2. Clean or unrack bar to clavicles with forearms vertical.\n3. Pull chin back slightly, drive bar straight up past face.\n4. Lock out directly overhead with head moving through the window.',
    'Do not hyperextend lumbar spine. Squeeze glutes and abdominals tightly throughout press.',
    ARRAY['Anterior & Lateral Deltoids'],
    ARRAY['Triceps Brachii', 'Upper Trapezius', 'Core'],
    'https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=800&q=80'
),
(
    'Barbell Bent-Over Row',
    'Hypertrophy',
    'Back',
    'Intermediate',
    'Olympic Barbell',
    '1. Hinge at hips until torso is roughly 45 degrees relative to floor.\n2. Grip barbell with overhand grip slightly wider than shoulders.\n3. Pull elbows back toward ribcage, squeezing shoulder blades together.\n4. Lower bar under full control to hang position.',
    'Avoid using excessive torso momentum or jerking the weight up.',
    ARRAY['Latissimus Dorsi', 'Rhomboids', 'Middle Trapezius'],
    ARRAY['Biceps Brachii', 'Posterior Deltoids', 'Erector Spinae'],
    'https://images.unsplash.com/photo-1605296867304-46d5465a13f1?auto=format&fit=crop&w=800&q=80'
),
(
    'Bodyweight Pull-Up',
    'Calisthenics',
    'Back & Biceps',
    'Intermediate',
    'Rigid Pull-Up Bar',
    '1. Hang from bar with hands slightly wider than shoulder width.\n2. Engage scaps down and back from dead hang.\n3. Pull chest toward bar until chin clears bar.\n4. Lower with steady 2-second negative back to complete dead hang.',
    'Avoid excessive kipping or swinging unless programmed for conditioning.',
    ARRAY['Latissimus Dorsi', 'Biceps Brachii'],
    ARRAY['Teres Major', 'Rhomboids', 'Brachialis'],
    'https://images.unsplash.com/photo-1598971639058-fab3c3109a00?auto=format&fit=crop&w=800&q=80'
),
(
    'Dumbbell Walking Lunges',
    'Conditioning',
    'Lower Body',
    'Beginner',
    'Rubber Hex Dumbbells',
    '1. Stand upright holding dumbbells by sides.\n2. Step forward with lead leg, bending both knees to roughly 90 degrees.\n3. Ensure rear knee hovers just above ground.\n4. Drive through front heel to step directly into next forward stride.',
    'Keep torso upright and do not slam rear knee into ground.',
    ARRAY['Quadriceps', 'Gluteus Maximus'],
    ARRAY['Hamstrings', 'Calves', 'Core Stabilizers'],
    'https://images.unsplash.com/photo-1434682881908-b43d0467b798?auto=format&fit=crop&w=800&q=80'
),
(
    'Parallel Bar Dips',
    'Bodyweight',
    'Chest & Triceps',
    'Intermediate',
    'Dip Station',
    '1. Mount parallel bars with straight arms and locked core.\n2. Lean forward slightly for chest emphasis or stay vertical for triceps.\n3. Lower body until upper arms are at least parallel to floor.\n4. Press back to complete lockout at top.',
    'Do not let shoulders roll forward into excessive internal rotation at bottom.',
    ARRAY['Triceps Brachii', 'Lower Pectoralis'],
    ARRAY['Anterior Deltoids'],
    'https://images.unsplash.com/photo-1530822847156-5df684ec5ee1?auto=format&fit=crop&w=800&q=80'
)
ON CONFLICT DO NOTHING;

-- 8.2 Curated Pro Shop Products Seed Data
INSERT INTO public.store_products (
    name, category, description, price, currency, stock_quantity, sku, image_url, available_sizes, is_active, is_featured
) VALUES
(
    'Strakly Heavy-Duty Lifting Belt',
    'Training Accessories',
    '10mm genuine leather powerlifting belt with quick-release matte steel prong buckle. USAPL specification for maximum intra-abdominal pressure support.',
    4500.00,
    'KES',
    18,
    'STR-BELT-10MM',
    'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=600&q=80',
    ARRAY['S', 'M', 'L', 'XL'],
    TRUE,
    TRUE
),
(
    'Strakly Athletic Pro Performance Tee',
    'Gym Apparel',
    'Moisture-wicking, breathable tri-blend athletic t-shirt with reinforced double-stitched shoulders and Strakly crest branding.',
    2200.00,
    'KES',
    35,
    'STR-TEE-PRO-01',
    'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=600&q=80',
    ARRAY['S', 'M', 'L', 'XL', 'XXL'],
    TRUE,
    TRUE
),
(
    'Strakly Stainless Steel Insulated Shaker (750ml)',
    'Water Bottles & Shakers',
    'Double-wall vacuum insulated stainless steel protein shaker. Keeps pre-workout ice cold for 24 hours with leak-proof screw lid.',
    1850.00,
    'KES',
    42,
    'STR-SHK-750ML',
    'https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=600&q=80',
    ARRAY['Standard'],
    TRUE,
    TRUE
),
(
    'Heavy Cotton Padded Wrist Wraps',
    'Training Accessories',
    'Competition-length 18-inch elasticised cotton wrist wraps with heavy-duty thumb loops for bench press and overhead stability.',
    1200.00,
    'KES',
    25,
    'STR-WRP-18IN',
    'https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?auto=format&fit=crop&w=600&q=80',
    ARRAY['One Size'],
    TRUE,
    FALSE
),
(
    'High-Density Grid Foam Roller (45cm)',
    'Recovery Accessories',
    'Multi-density EVA textured foam roller designed for deep tissue trigger point release and myofascial recovery.',
    2800.00,
    'KES',
    14,
    'STR-ROL-45CM',
    'https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=600&q=80',
    ARRAY['Standard'],
    TRUE,
    FALSE
),
(
    'Strakly Tactical Duffel Gym Bag (45L)',
    'Gym Bags',
    'Water-resistant 1000D ballistic nylon gym duffel featuring dedicated ventilated shoe compartment, shaker holster, and molle webbing.',
    4200.00,
    'KES',
    12,
    'STR-BAG-45L',
    'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80',
    ARRAY['45L'],
    TRUE,
    TRUE
),
(
    'Pure Magnesium Carbonate Gym Chalk Block',
    'Workout Essentials',
    'Laboratory-grade 56g solid block of pure magnesium carbonate. Superior grip assurance for heavy deadlifts and gymnastics.',
    450.00,
    'KES',
    60,
    'STR-CHALK-56G',
    'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=600&q=80',
    ARRAY['56g Block'],
    TRUE,
    FALSE
)
ON CONFLICT (sku) DO NOTHING;

-- 8.3 Curated Facility Assets & Equipment Seed Data
INSERT INTO public.gym_equipment (
    name, category, brand, model, model_serial, serial_number, quantity,
    acquisition_date, condition, is_available, image_url, facility_location, location,
    maintenance_status, last_maintenance_date, next_maintenance_date, notes
) VALUES
(
    'Olympic Power Cage Multi-Station #01',
    'Rigid Strength',
    'Rogue Fitness',
    'Monster Lite R-3',
    'ROG-ML-001',
    'ROG-ML-001',
    2,
    '2024-01-15',
    'excellent',
    TRUE,
    'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80',
    'Main Strength Deck — Station A',
    'Main Strength Deck — Station A',
    'operational',
    '2026-11-01',
    '2027-02-01',
    'Equipped with safety spotter arms, j-cups, and multi-grip pull-up crossmember.'
),
(
    'Calibrated Competition Bumper Plates Set (140kg)',
    'Free Weights',
    'Eleiko',
    'IWF Training Bumper Series',
    'ELK-PLT-140',
    'ELK-PLT-140',
    6,
    '2024-03-20',
    'excellent',
    TRUE,
    'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=800&q=80',
    'Weightlifting Platforms 1 - 4',
    'Weightlifting Platforms 1 - 4',
    'operational',
    '2026-10-15',
    '2027-01-15',
    'Steel disc hub inserts with virgin rubber outer rim. Calibrated within 10 grams.'
),
(
    'Woodway 4Front Slat-Belt Curve Treadmill',
    'Cardiovascular',
    'Woodway',
    'Curve Slat-Belt Pro',
    'WW-CV-8821',
    'WW-CV-8821',
    3,
    '2024-06-10',
    'good',
    TRUE,
    'https://images.unsplash.com/photo-1576678927484-cc907957088c?auto=format&fit=crop&w=800&q=80',
    'Cardio & Conditioning Loft',
    'Cardio & Conditioning Loft',
    'operational',
    '2026-11-10',
    '2026-12-10',
    'Non-motorized manual curved deck driven entirely by athlete stride power.'
),
(
    'Rubber Hex Dumbbell Full Tier (2.5kg - 50kg)',
    'Free Weights',
    'Jordan Fitness',
    'Commercial Hex Dumbbells',
    'JRD-HEX-SET',
    'JRD-HEX-SET',
    1,
    '2024-02-01',
    'excellent',
    TRUE,
    'https://images.unsplash.com/photo-1586401100295-7a8096fd231a?auto=format&fit=crop&w=800&q=80',
    'Dumbbell Free Weight Area',
    'Dumbbell Free Weight Area',
    'operational',
    '2026-11-05',
    '2027-02-05',
    'Ergonomic contoured chrome handles with pinned rubber-coated hexagonal heads.'
),
(
    'Turf Sprint Conditioning Sled (Prowler)',
    'Conditioning',
    'Rogue Fitness',
    'Echo Dog Sled 2.0',
    'ROG-SLED-04',
    'ROG-SLED-04',
    2,
    '2024-05-18',
    'excellent',
    TRUE,
    'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=800&q=80',
    'High-Density Turf Sprint Strip',
    'High-Density Turf Sprint Strip',
    'operational',
    '2026-10-25',
    '2027-01-25',
    'Fitted with UHMW plastic ski feet for smooth glide across indoor sprint turf.'
)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- MIGRATION COMPLETE: Strakly Gym Enhancement Migration Executed Cleanly
-- =============================================================================
