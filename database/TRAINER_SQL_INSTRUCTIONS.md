# STRAKLY GYM MANAGEMENT SYSTEM — TRAINER PORTAL SQL MIGRATION INSTRUCTIONS

This document provides exact instructions for applying the `database/trainer.sql` migration on your Supabase PostgreSQL database.

---

## 1. WHAT THIS MIGRATION IMPLEMENTS

The `database/trainer.sql` script sets up all database tables, columns, indexes, Row-Level Security (RLS) policies, and seed data for the **Trainer Portal**, **Coaching Workspace**, **Specialised Coaching Programmes (Part 5)**, and **Public Website (Part 6)**:

1. **`public.trainer_details` extensions**:
   - `certifications`: CSCS, USAW, NASM, FMS credentials.
   - `coaching_philosophy`: Coach's training methodology.
   - `experience_years`: Years of coaching experience.
   - `profile_status`: `draft` | `pending` | `approved` | `rejected`.
   - `is_published`: Controls visibility on the public website.
   - `rating` & `review_count`: Verified coach ratings.
   - `submitted_at`, `approved_at`, `approved_by`, `rejection_reason`.

2. **`public.trainer_availability`**:
   - Weekly working hours (Monday through Sunday).
   - Time slots (`start_time`, `end_time`), `is_available` toggle, and notes.

3. **`public.fitness_assessments`**:
   - Athlete evaluations, fitness objectives, strength/endurance/mobility observations.
   - Body measurements stored in structured `JSONB`.
   - Actionable recommendations and `next_review_date`.

4. **`public.athlete_checkins`**:
   - Daily/weekly athlete check-in logs with energy ratings (1–5), soreness (1–5), nutrition adherence.
   - Direct coach feedback and review status (`pending`, `reviewed`).

5. **`public.trainer_programmes` (Part 5)**:
   - Specialised coaching programmes proposed by trainers for Admin approval.
   - Duration, session count, target audience, category, proposed KES cash price.
   - Status tracking (`draft`, `pending`, `approved`, `rejected`) and public publication toggle.

6. **`public.pt_sessions`**:
   - 1-on-1 personal training sessions with date, time, duration, focus area, notes, and completion tracking.

7. **`public.member_testimonials` (Part 6.9)**:
   - Real member transformation stories and verified quotes displayed on the public homepage.

8. **Fully Safe & Idempotent Execution**:
   - Safely adds missing columns (`hourly_rate`, `is_active`, `trainer_number`, `certifications`, `duration_minutes`) if tables already existed.
   - Gracefully relaxes `assigned_by` null constraints on `trainer_assignments` so seed records and automatic assignments run without conflict.
   - Populates certified coach profiles, availability schedules, assigned athletes, sample fitness assessments, check-ins with coach feedback, approved specialised programmes, and athlete testimonials.

---

## 2. HOW TO EXECUTE IN SUPABASE

1. Open your Supabase project: [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. In the left navigation, click on **SQL Editor**.
3. Click **+ New query**.
4. Open `database/trainer.sql` in this project and copy its entire contents.
5. Paste into the Supabase SQL Editor and click the green **Run** button (or press `Ctrl+Enter` / `Cmd+Enter`).
6. You will see:
   ```text
   Success. "Trainer Portal database schema and seed data successfully initialized."
   ```

---

## 3. VERIFICATION QUERY

Run this quick check in your Supabase SQL Editor to verify all trainer tables:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'trainer_details', 
    'trainer_availability', 
    'fitness_assessments', 
    'athlete_checkins', 
    'trainer_programmes',
    'pt_sessions',
    'member_testimonials'
  );
```
