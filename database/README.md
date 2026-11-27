# LEVY KIRINYA GYM MANAGEMENT SYSTEM — DATABASE SETUP GUIDE

## Overview

The database architecture for the Levy Kirinya Gym Management System is built on PostgreSQL via Supabase. It provides complete data models for:
- Role-based Authentication (`admin`, `trainer`, `member`)
- Member & Trainer Profiles
- Membership Packages & Subscriptions
- Strict Cash-Only Payment Recording & Receipts
- Manual Front-Desk Attendance (Strictly NO QR/Scanning)
- Trainer Assignments (Self-Guided vs Coached Member)
- Exercise Library & Visual Workout Plan Builder
- Member Workout Logging & Fitness Progress Tracking
- Equipment Inventory & Maintenance Logs
- Shared Community Hub (Posts, Comments, Reactions, Groups, Messages)
- Notifications & System Announcements
- Append-Only Audit Logging
- Dynamic Platform Settings & Services

---

## 1. SQL Setup File Location

The master SQL initialization file is located at:
`database/gym_management_setup.sql`

---

## 2. Manual Execution Instructions

1. Log into your [Supabase Dashboard](https://supabase.com/dashboard).
2. Open your Supabase project (or create a new project).
3. In the left navigation menu, click **SQL Editor**.
4. Click **New Query**.
5. Open `database/gym_management_setup.sql`, copy all text, and paste it into the SQL Editor.
6. Click **Run** (or press `Ctrl + Enter`).
7. Confirm that the query succeeds without errors.

---

## 3. Verify Tables and RLS Policies

1. In the Supabase Dashboard, click **Table Editor**.
2. Verify that the following tables exist:
   - `profiles`, `member_details`, `trainer_details`
   - `membership_plans`, `member_subscriptions`
   - `cash_payments`, `manual_attendance`
   - `trainer_assignments`, `services`, `fitness_classes`, `class_bookings`
   - `exercise_library`, `workout_plans`, `workout_plan_exercises`, `workout_logs`, `fitness_progress`
   - `gym_equipment`, `equipment_maintenance`
   - `community_groups`, `community_group_members`, `community_posts`, `community_comments`, `community_reactions`, `community_reports`, `private_messages`
   - `notifications`, `announcements`, `audit_logs`, `platform_settings`
3. Click on **Authentication** -> **Policies** to confirm that Row Level Security (RLS) is active for every table.

---

## 4. Supabase Storage Buckets

In the Supabase Dashboard, go to **Storage** and create the following buckets:

| Bucket Name | Privacy | Allowed MIME Types | Purpose |
|---|---|---|---|
| `gym-public` | Public | images/*, videos/* | Gym branding, facilities, services, hero banners |
| `avatars` | Public | images/* | Member and trainer profile photos |
| `community-uploads` | Public | images/* | Community feed posts and progress photos |

---

## 5. Setting up the First Administrator Account

Because public registration defaults strictly to the `member` role, create your initial administrator securely:

1. In Supabase Dashboard, navigate to **Authentication** -> **Users**.
2. Click **Add User** -> **Create User**.
3. Enter the administrator's email (e.g. `admin@levygym.co.ke`) and a secure password. Check **Auto Confirm Email**.
4. Copy the generated User UUID (e.g. `d3b07384d113...`).
5. Go to **SQL Editor** -> **New Query** and execute:
```sql
INSERT INTO public.profiles (id, email, full_name, role)
VALUES ('<PASTE-USER-UUID-HERE>', 'admin@levygym.co.ke', 'Levy Kirinya Admin', 'admin')
ON CONFLICT (id) DO UPDATE SET role = 'admin';
```
6. The administrator can now log into the Administrator Portal at `/login`.

---

## 6. Configuring Environment Variables

Create your `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Edit `.env` and configure:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
SECRET_KEY=your-flask-secret-key
```

The Flask application includes a resilient client architecture: if `.env` does not have credentials configured yet, the app starts smoothly and presents clear, polished configuration banners and empty states rather than crashing or showing fake data.
