# STRAKLY ADMIN PORTAL — DESIGN AUDIT & REDESIGN BLUEPRINT

## EXECUTIVE SUMMARY
This document establishes the comprehensive visual audit and design transformation roadmap for the **Strakly Gym Management System Admin Portal**.

---

## 1. DESIGN IDENTITY: STRAKLY PEARL, FOREST & ROSE

The Admin Portal uses the premium, light-mode **Strakly Pearl, Forest and Rose** design language:

```css
:root {
  --admin-bg-pearl: #FBF8F6;          /* Clean pearl canvas */
  --admin-card-cloud: #FFFFFF;        /* Elevated white card */
  --admin-blush-hover: #F6EBE8;       /* Subtle raised/hover surface */
  --admin-border-line: #E9DFDB;       /* Warm neutral border line */
  --admin-ink: #1E2B25;               /* Deep forest dark ink text */
  --admin-muted: #566860;             /* Slate muted metadata */
  --admin-forest: #2F6B4F;            /* Primary brand forest green */
  --admin-forest-hover: #285C43;      /* Deep forest button hover */
  --admin-forest-tint: rgba(47, 107, 79, 0.10); /* Soft forest background tint */
  --admin-rose: #B64A6E;              /* Sophisticated accent rose */
  --admin-rose-tint: rgba(182, 74, 110, 0.10);  /* Soft rose background tint */
  --admin-success: #1F7A4A;
  --admin-warning: #E0A030;
  --admin-warning-text: #8A5A00;
  --admin-danger: #C0392B;
  --admin-info: #2B6CB0;
  --admin-signature-gradient: linear-gradient(135deg, #FCF9F7 0%, #F8EDEA 52%, #EAF2EC 100%);
  --admin-card-shadow: 0 1px 2px rgba(30,43,37,.04), 0 12px 28px rgba(30,43,37,.05);
}
```

---

## 2. AUDIT OF ALL 18 ADMIN MODULES

| No. | Module Name | Route | Current Template | Visual Reference & Target Transformation |
|---|---|---|---|---|
| 1 | **Dashboard** | `/admin/dashboard` | `admin/dashboard.html` | Fitness Management Dashboard: Personalized greeting, KPI cards, Membership Growth line chart, Membership Status doughnut, Cash collection bar chart, Attendance trends, recent activities. |
| 2 | **Athletes** | `/admin/members` | `admin/members.html` | Member Management Dashboard: Athlete identity cells with avatars/initials, KPI cards, search toolbar, status filters, refined management table with view/edit/delete. |
| 3 | **Plans & Tiers** | `/admin/plans` | `admin/plans.html` | Subscription Management Dashboard: Package card comparison view, price tags in KES, duration, benefits pills, add/edit/archive modals. |
| 4 | **Subscriptions** | `/admin/subscriptions` | `admin/subscriptions.html` | Subscription Workspace: KPI summary cards (active, expiring, expired), date filters, detailed athlete plan subscription table with renew/cancel actions. |
| 5 | **Cash Payments** | `/admin/payments` | `admin/payments.html` | Financial Management: Strictly cash transactions, lifetime collection cards, collection trends bar chart, verified receipts table, receipt preview modal. |
| 6 | **Attendance** | `/admin/attendance` | `admin/attendance.html` | Front-Desk Attendance: Strictly manual check-in search bar, athlete verification card, today's check-in timeline table, daily attendance distribution chart. |
| 7 | **Coaching Staff** | `/admin/trainers` | `admin/trainers.html` | Coaching Directory: Profile cards with coach photos/initials, specialisation tags, assigned athlete counters, add/edit/assign modals. |
| 8 | **Class Schedule** | `/admin/classes` | `admin/classes.html` | Class Scheduling SaaS: Timetable view, time blocks, category colour badges, capacity & bookings indicators, create/edit class drawer. |
| 9 | **Movement Library** | `/admin/exercises` | `admin/exercises.html` | Photo-led Movement Library: Exercise cards with muscle group badges, difficulty tags, equipment cues, searchable catalogue, add/edit modal. |
| 10 | **Facility Services** | `/admin/services` | `admin/services.html` | Service Management: Service cards with imagery, pricing in KES, public toggle, add/edit/archive modals. |
| 11 | **Assets & Gear** | `/admin/equipment` | `admin/equipment.html` | Equipment Inventory: Asset status summary (operational, maintenance, damaged), equipment grid with brand, condition, maintenance history log modal. |
| 12 | **Community Hub** | `/admin/community` | `admin/community.html` | Social Administration: Activity feed, member posts, comments, moderation side panel with reported content actions. |
| 13 | **Announcements** | `/admin/announcements` | `admin/announcements.html` | Editorial Publisher: Announcement preview cards, publish status badges, audience tags, creation modal. |
| 14 | **Notifications** | `/admin/notifications` | `admin/notifications.html` | Activity Centre: Categorised inbox cards, unread indicators, recipient meta, mark all as read. |
| 15 | **Operational Reports**| `/admin/reports` | `admin/reports.html` | PULSEFORM Fitness Analytics: Multi-category tabs (Membership, Cash, Attendance, Classes), high-res Chart.js visualizations, CSV/Print exports. |
| 16 | **Audit Logs** | `/admin/audit-logs` | `admin/audit_logs.html` | Administrative Activity: Chronological event timeline, user initials, module tags, action badges, inspect details drawer/modal. |
| 17 | **User Accounts** | `/admin/users` | `admin/users.html` | User Administration: Account status KPIs, searchable directory, role badges (admin, trainer, member), suspend/reactivate, password reset, delete. |
| 18 | **Facility Settings** | `/admin/settings` | `admin/settings.html` | SaaS Settings Centre: Tabbed configuration (General, Branding, Hours, Contact, Receipts), styled forms, save feedback. |

---

## 3. STRICT REFACTORING PRINCIPLES
1. **Preserve All Existing Routes:** Zero URL changes.
2. **Preserve Working Database Operations:** Keep all existing CRUD endpoints, form field names, and methods.
3. **No Fake / Hardcoded Data:** Use real Jinja loops over query results with graceful empty states.
4. **Strict Cash Only & Manual Attendance:** Honor physical cash rules and receptionist-verified check-ins.
5. **No Visual Overlap or Broken Mobile Drawers:** Independent content scrolling with 232px desktop sidebar and collapsible mobile drawer.
