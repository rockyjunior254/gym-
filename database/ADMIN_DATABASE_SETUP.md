# LEVY KIRINYA GYM MANAGEMENT SYSTEM
## ADMIN PORTAL SUPABASE MIGRATION & EXECUTION GUIDE

This guide provides instructions for manually executing the Admin Portal database extension and migration script in your Supabase project.

---

## 1. Migration File Location

The SQL migration script is located at:
`database/admin_portal_setup.sql`

---

## 2. What This Migration Does

1. **Safe Schema Alterations:**
   - Adds `is_archived` flags to `profiles`, `membership_plans`, `services`, `fitness_classes`, `gym_equipment`, and `exercise_library` to support soft-deletion and preserve historical data.
   - Adds operational tracking columns (e.g. `cancellation_reason`, `reversal_reason`, `warranty_expiry`, `action_url`, `resolution_notes`).
2. **Administrator Role Promotion:**
   - Safely and idempotently promotes the administrator account `achiengpatricia32@gmail.com` to the `admin` role by matching its UUID in `auth.users`.
   - If the user account has not yet been created under Supabase Authentication, create the user in the Supabase Dashboard under **Authentication -> Users** and run the script.
3. **Audit Log Append-Only Protection:**
   - Installs a database trigger `trg_audit_logs_immutable` that prevents updates or deletions to `audit_logs`, guaranteeing an immutable security audit trail.
4. **Attendance Eligibility & Duplicate Protection:**
   - Installs `public.check_member_attendance_eligibility(member_id)` to verify active subscription validity in a single database roundtrip.
5. **Real-time Dashboard Analytics Function:**
   - Installs `public.get_admin_dashboard_kpis()` returning live aggregates for:
     - Total Members
     - Active Memberships
     - Expired Memberships
     - New Registrations (last 30 days)
     - Today's Attendance Check-ins
     - Total Cash Collected
     - Upcoming Classes
     - Active Trainers
6. **Supabase Storage Buckets:**
   - Ensures configuration for `gym-public`, `avatars`, and `community-uploads` with public read policies.
7. **Performance Indexes & Admin RLS Policies:**
   - Creates composite indexes for common search filters and ensures users with `role = 'admin'` have full administrative access across all tables.

---

## 3. Manual Execution Steps

1. Log into your [Supabase Project Dashboard](https://supabase.com/dashboard).
2. Select your project: `gtqiyezxgcluofodspcs`.
3. In the left sidebar, click on **SQL Editor**.
4. Click **New Query** (top left).
5. Open `database/admin_portal_setup.sql`, copy its entire content, and paste it into the editor.
6. Click **Run** (green button at bottom right, or press `Ctrl + Enter`).
7. Confirm the result displays `Success. No rows returned` or completion notices without errors.

---

## 4. Verification Queries

Run these quick verification queries in the Supabase SQL Editor:

### A. Verify Administrator Profile Promotion
```sql
SELECT id, email, full_name, role, is_active, is_archived
FROM public.profiles
WHERE lower(email) = lower('achiengpatricia32@gmail.com');
```
*Expected: Returns a row with `role = 'admin'` and `full_name = 'patricia achieng'`.*

### B. Verify Dashboard KPIs Function
```sql
SELECT public.get_admin_dashboard_kpis();
```
*Expected: Returns a JSON object with live counts for all 8 core metrics.*

### C. Verify Audit Log Immutable Trigger
```sql
-- Attempting an update on audit logs will safely fail with an exception
UPDATE public.audit_logs SET action_type = 'MODIFIED' WHERE id IS NOT NULL;
```
*Expected: Error `Audit logs are append-only. Modification or deletion is strictly forbidden.`*

---

## 5. Environment Variables

Your `.env` file should contain the valid Supabase connection details:
```env
SUPABASE_URL=https://gtqiyezxgcluofodspcs.supabase.co
SUPABASE_KEY=sb_publishable_Dp-L_mVtn5zpm4Vurl1WdQ_TMLD6FD6
SUPABASE_SECRET_KEY=sb_secret_P0ZBcuCvKe2WLL1TU-v2og_tbL1x2Df
SECRET_KEY=your-flask-session-secret-key
```
