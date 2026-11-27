# STRAKLY GYM MANAGEMENT SYSTEM — TRAINEE SQL MIGRATION INSTRUCTIONS

This document provides clear, step-by-step instructions for executing the `database/trainee.sql` migration script on your Supabase PostgreSQL instance.

---

## 1. PURPOSE OF THIS MIGRATION

The `database/trainee.sql` script creates the dedicated database schema required for the complete, premium **FitPulse-inspired Trainee Portal**.

This migration introduces:
1. `public.membership_requests` — Member plan upgrade, renewal, downgrade, freeze, and cancellation requests.
2. `public.member_pt_wallets` — Tracks prepaid 1-on-1 personal training session credits.
3. `public.pt_sessions` — 1-on-1 personal training bookings with assigned coaches.
4. `public.coach_requests` — Requests to assign or change a dedicated personal trainer.
5. `public.member_goals` — Trainee fitness goals with target values, progress tracking, and deadlines.
6. `public.member_personal_records` — Personal records (PRs) and estimated 1-rep maximums for key movements.
7. `public.member_progress_photos` — Secure, private progress photo logs and notes.
8. `public.fitness_challenges` — Active club-wide challenges (Consistency streaks, 1000lb club, Cardio assaults).
9. `public.challenge_participants` — Challenge enrollments and member milestone tracking.
10. `public.member_achievements` — Unlocked trainee badges and milestone rewards.
11. `public.equipment_reservations` — Checkout & reservation of gym gear (weightlifting belts, resistance bands, mats).
12. `public.store_products` — Strakly branded apparel, gear, shakers, and accessories.
13. `public.store_orders` — Member merchandise reservations with **STRICT CASH ON COLLECTION** at the gym front desk.
14. `public.service_inquiries` — Trainee booking requests for sauna, physiotherapy, and recovery services.
15. `public.support_tickets` — In-app help desk with ticket numbers, categories, and direct management responses.
16. `public.member_settings` — Personal notification preferences, coach visibility, and privacy controls.

---

## 2. HOW TO RUN THE MIGRATION IN SUPABASE

### Step 1: Open Supabase Dashboard
1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard) and log in.
2. Select your Strakly Gym project.

### Step 2: Open SQL Editor
1. In the left navigation sidebar of your Supabase project, click on **SQL Editor**.
2. Click **+ New query**.

### Step 3: Paste and Execute
1. Open the file `database/trainee.sql` in this project.
2. Copy the entire contents of the file.
3. Paste the SQL query into the Supabase SQL Editor.
4. Click the green **Run** button (or press `Ctrl+Enter` / `Cmd+Enter`).

### Step 4: Confirm Success
You should see:
```text
Success. No rows returned (or rows affected).
```
All 16 tables will now be created with cascading foreign keys to `public.profiles`, `public.gym_equipment`, `public.membership_plans`, and `public.services`. Sample challenges and store merchandise will also be seeded automatically.

---

## 3. VERIFICATION QUERY

To verify that all trainee tables have been created correctly, run this quick check in the SQL Editor:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'membership_requests', 
    'member_pt_wallets', 
    'pt_sessions', 
    'coach_requests', 
    'member_goals', 
    'member_personal_records', 
    'member_progress_photos', 
    'fitness_challenges', 
    'challenge_participants', 
    'member_achievements', 
    'equipment_reservations', 
    'store_products', 
    'store_orders', 
    'service_inquiries', 
    'support_tickets', 
    'member_settings'
  )
ORDER BY table_name;
```

You should see all 16 table names returned.
