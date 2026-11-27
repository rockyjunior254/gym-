# STRAKLY GYM MANAGEMENT SYSTEM — MANUAL DATABASE EXECUTION INSTRUCTIONS
**Target Migration File:** `database/admin.sql`  
**Target Administrator Account:** `achiengpatricia32@gmail.com`  
**Execution Environment:** Supabase PostgreSQL SQL Editor

---

## Instructions for the Project Owner

Follow these steps to manually execute the single consolidated administrative SQL migration:

1. Log into your **Supabase Dashboard**: [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project: **`gtqiyezxgcluofodspcs`**
3. Navigate to the **SQL Editor** tab in the left-hand sidebar (icon: `>_`).
4. Click **+ New Query** to open a clean query tab.
5. Open the local file `database/admin.sql` on your machine, copy all contents, and paste into the Supabase SQL Editor.
6. Click **Run** (or press `Cmd + Enter` / `Ctrl + Enter`).

> [!NOTE]
> **Resolved Errors (42703, 42P13 & 42P01):**
> 1. **ERROR 42703 (column "check_out_time" does not exist):** Fixed! The manual front desk attendance system uses `check_in_time`. The nonexistent `check_out_time` column has been completely removed from both `manual_attendance` and `public.attendance` view.
> 2. **Relation `public.payments` does not exist (42P01):** The database stores payments in `public.cash_payments`, attendance in `public.manual_attendance`, classes in `public.fitness_classes`, and services in `public.services`. `database/admin.sql` is 100% self-contained: it creates all base tables with `CREATE TABLE IF NOT EXISTS`, adds compatibility views (`public.payments`, `public.attendance`, `public.classes`, `public.gym_services`, `public.exercises`, `public.equipment_maintenance_logs`), and creates all indexes and functions on the primary tables.
> 3. **Input Parameter Mismatch (42P13):** `admin.sql` executes `DROP FUNCTION IF EXISTS public.check_member_attendance_eligibility(UUID);` and uses `target_member_id UUID` prior to creation. All functions and triggers are dropped cleanly beforehand.

---

## Verification Queries

To confirm that all administrative extensions and account elevation succeeded, run the following verification query in the SQL Editor:

```sql
-- 1. Verify administrator role promotion
SELECT id, email, full_name, role, is_active 
FROM public.profiles 
WHERE lower(email) = lower('achiengpatricia32@gmail.com');

-- 2. Test authoritative KPI function
SELECT public.get_admin_dashboard_kpis();

-- 3. Verify attendance view executes cleanly without check_out_time
SELECT * FROM public.attendance LIMIT 1;

-- 4. Verify gym services compatibility view exists
SELECT COUNT(*) FROM public.gym_services;
```

Expected result:
- The user `achiengpatricia32@gmail.com` has `role = 'admin'` and `is_active = true`.
- The KPI function returns a JSON object with valid counts.
- `public.attendance` queries cleanly using `check_in_time`.
- The `gym_services` view is created and operational.
