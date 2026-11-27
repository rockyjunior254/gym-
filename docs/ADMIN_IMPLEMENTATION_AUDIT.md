# STRAKLY GYM MANAGEMENT SYSTEM — ADMIN PORTAL IMPLEMENTATION AUDIT & DIAGNOSIS
**Application:** Strakly (formerly Levy Kirinya Gym Management System)  
**Date:** November 26, 2026  
**Auditor:** Senior Full-Stack Software Engineer & Database Architect  
**Admin Elevation Target:** `achiengpatricia32@gmail.com`

---

## 1. Executive Diagnosis & Root Causes Found

### 1.1 The Critical Trainer Management Bug Diagnosed
- **Root Cause:** In `app/templates/admin/trainers.html`, the modal form `#addTrainerModal` submitted to `action="{{ url_for('admin.trainers') }}"` with fields `full_name`, `email`, `phone`, `specialisations`, `bio`.
- **Backend Mismatch:** In `app/routes/admin.py`, the `POST` handler for `/trainers` **only** expected `member_id` and `trainer_id` to assign an existing trainer to an athlete (`trainer_assignments` table). It completely lacked a branch to handle trainer creation or submitted to the wrong endpoint! When an administrator submitted the "Add Coach" form, `member_id` and `trainer_id` were `None`, causing a database null constraint failure or foreign key crash!
- **Resolution:**
  1. Add a dedicated route `/admin/trainers/create` and `/admin/trainers/edit/<id>`, `/admin/trainers/suspend/<id>`, `/admin/trainers/reassign` or cleanly distinguish form submission actions.
  2. Implement backend Supabase Auth user creation for trainers via the service-role client on the server, insert into `profiles` (role: `trainer`), and upsert into `trainer_details` with specialisations array and bio.

### 1.2 User Accounts & Role Permissions Diagnosis
- **Existing State:** User accounts page listed users and allowed updating roles, but lacked a complete "Add User" workflow with server-side Auth creation (`supabase.auth.admin.create_user`).
- **Resolution:** Implement a robust `create_user` backend service that registers the Auth identity and initializes the appropriate profile and detail records (e.g. `member_details` or `trainer_details`) without exposing keys.

### 1.3 Branding "Levy Kirinya" -> "Strakly"
- The application contains product references to "Levy Kirinya" across `public.py`, `__init__.py`, `base_public.html`, `main.js`, and public/admin templates.
- **Resolution:** Cleanly replace all product branding with **Strakly**, adhering strictly to:
  - Header & wordmark: **STRAKLY**.
  - Browser titles: `<title>Strakly | ...</title>`.
  - Homepage presentation: Fictional English-style names (e.g., James Scott, Oliver Bennett, Daniel Brooks, Emily Carter, Sophia Mitchell) for sample visual cards without touching real database user identities.

### 1.4 Database Migration Architecture (`database/admin.sql`)
- The repository previously contained `gym_management_setup.sql` and `admin_portal_setup.sql`.
- In strict adherence to Section 24, all schema extensions, safe table alterations, triggers, functions, storage policies, and the idempotent elevation of `achiengpatricia32@gmail.com` must be consolidated into one single, clean, self-contained file:
  **`database/admin.sql`**
- An execution guide **`database/ADMIN_SQL_INSTRUCTIONS.md`** must accompany it.

---

## 2. Admin Modules Audit Matrix

| # | Module | Discovered Defect | Required Implementation / Repair | Status |
|---|---|---|---|---|
| 1 | **Dashboard** | Static period filter params; needs complete sync with all 18 modules. | Real-time KPI aggregation, 4 Chart.js charts, quick action modals. | DIAGNOSED |
| 2 | **Users** | Lacked Add User workflow and password reset initiation. | Full User CRUD: Create User via Auth, list, edit, suspend/reactivate, controlled delete. | TO BE REPAIRED |
| 3 | **Members** | Basic listing existed; edit/status toggle required validation. | Full Member CRUD: Add athlete with membership number, edit profile, detail tabs, archive. | TO BE REPAIRED |
| 4 | **Plans & Packages** | Package creation form existed; edit modal missing. | Full Package CRUD: Create, edit modal, price KES, duration, archive/activate toggle. | TO BE REPAIRED |
| 5 | **Subscriptions** | Activation route existed; edit/cancel/renew workflows incomplete. | Subscriptions CRUD: Request form, activation on cash confirmation, cancellation, expiry tracking. | TO BE REPAIRED |
| 6 | **Payments & Receipts** | Record payment worked; reversal lacked full reason validation and print layout refinement. | **Strict cash only**. Unique receipt (`RCP-YYYY-XXXX`), printable receipt modal, reversal with mandatory audit reason. | TO BE REPAIRED |
| 7 | **Attendance** | Manual check-in form worked; eligibility validation required visual feedback. | **Strictly manual front-desk lookup** (NO QR/barcode). Eligibility clearance, duplicate prevention, daily attendance log. | TO BE REPAIRED |
| 8 | **Trainers** | **CRITICAL BUG**: "Add Coach" modal crashed because route expected `member_id` assignment. | Separate Create Trainer route, link Auth account, insert `trainer_details`, member assignment & reassignment. | TO BE REPAIRED |
| 9 | **Classes & Bookings** | Scheduling form existed; capacity check and cancellation workflow needed. | Class CRUD: Create session, assign coach, enforce capacity limit on booking, cancel/archive class. | TO BE REPAIRED |
| 10 | **Workout & Exercises**| Exercise list existed; exercise edit and category filtering needed. | Exercise library CRUD: target muscle groups, instructions, difficulty levels, equipment required. | TO BE REPAIRED |
| 11 | **Gym Services** | Creation modal existed; edit service and image handling needed. | Full Services CRUD: Category, description, amenities, publish toggle, dynamic sync with public homepage. | TO BE REPAIRED |
| 12 | **Equipment** | Inventory list existed; maintenance scheduling modal missing. | Equipment CRUD & Maintenance: Asset condition update, maintenance logging and history. | TO BE REPAIRED |
| 13 | **Community Hub** | Post moderation existed; reported post review workflow needed. | Community oversight: Post feed, administrative hide/unhide with audit reason, group overview. | TO BE REPAIRED |
| 14 | **Announcements** | Create announcement existed; edit and audience targeting needed. | Announcements CRUD: Target audience (`all`, `member`, `trainer`), publish/unpublish toggle, archive. | TO BE REPAIRED |
| 15 | **Notifications** | Notification broadcast existed; mark as read & recipient filter needed. | Notifications dispatch: Facility-wide broadcast and direct athlete alerts with unread counter. | TO BE REPAIRED |
| 16 | **Reports & Analytics**| Basic 5 reports; needs expansion and date range filtering. | 10+ operational reports, date filters, printable layout, streaming CSV export. | TO BE REPAIRED |
| 17 | **Audit Logs** | Append-only log table existed; actor and action filtering needed. | Security audit log: actor, role, action, record ID, before/after values, search & date filter. | TO BE REPAIRED |
| 18 | **Settings** | Basic settings existed; complete Strakly branding and business rules needed. | Gym settings: name ("Strakly"), logo, contact, operating hours, cash policy toggle, public content sync. | TO BE REPAIRED |
