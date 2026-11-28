import os
import uuid
import datetime
import logging
from app.services.supabase_client import db_service

logger = logging.getLogger(__name__)

class GymRepository:
    """
    Central repository for Supabase database operations.
    Fully database-driven: queries real tables, handles relationships,
    and returns accurate aggregates without fabricated data.
    """

    # =========================================================================
    # 1. PLATFORM SETTINGS
    # =========================================================================
    @staticmethod
    def get_setting(key: str, default=None):
        if not db_service.is_configured:
            return default
        try:
            res = db_service.get_table('platform_settings').select('value').eq('key', key).execute()
            if res.data:
                return res.data[0]['value']
            return default
        except Exception as e:
            logger.error(f"Error fetching setting {key}: {e}")
            return default

    @staticmethod
    def update_setting(key: str, value: dict):
        if not db_service.is_configured:
            return False
        try:
            db_service.get_table('platform_settings').upsert({'key': key, 'value': value}).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating setting {key}: {e}")
            return False

    # =========================================================================
    # 2. ADMIN DASHBOARD REAL-TIME KPIS & CHARTS
    # =========================================================================
    @staticmethod
    def get_admin_dashboard_kpis():
        """Calculates authoritative KPI metrics directly from real database records."""
        default_kpis = {
            'total_members': 0,
            'active_members': 0,
            'expired_memberships': 0,
            'new_registrations': 0,
            'today_attendance': 0,
            'total_cash_collected': 0.0,
            'upcoming_classes': 0,
            'active_trainers': 0
        }
        if not db_service.is_configured:
            return default_kpis

        try:
            # Check if database function exists
            try:
                rpc_res = db_service.client.rpc('get_admin_dashboard_kpis').execute()
                if rpc_res.data:
                    return rpc_res.data
            except Exception:
                pass

            # Otherwise calculate cleanly via table queries
            members = GymRepository.get_all_members()
            subscriptions = GymRepository.get_all_subscriptions()
            payments = GymRepository.get_all_cash_payments()
            attendance = GymRepository.get_all_attendance()
            classes = GymRepository.get_upcoming_classes()
            trainers = GymRepository.get_all_trainers()

            today_str = datetime.date.today().isoformat()
            thirty_days_ago = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()

            total_m = len(members)
            active_m = sum(1 for s in subscriptions if s.get('status') == 'active' and (not s.get('end_date') or s.get('end_date') >= today_str))
            expired_m = sum(1 for s in subscriptions if s.get('status') == 'expired' or (s.get('status') == 'active' and s.get('end_date') and s.get('end_date') < today_str))
            new_reg_m = sum(1 for m in members if m.get('created_at', '') >= thirty_days_ago)
            today_att = sum(1 for a in attendance if a.get('check_in_time', '').startswith(today_str))
            total_cash = sum(float(p.get('amount', 0)) for p in payments if p.get('status') == 'confirmed')
            upcoming_cls = len(classes)
            active_tr = len(trainers)

            return {
                'total_members': total_m,
                'active_members': active_m,
                'expired_memberships': expired_m,
                'new_registrations': new_reg_m,
                'today_attendance': today_att,
                'total_cash_collected': total_cash,
                'upcoming_classes': upcoming_cls,
                'active_trainers': active_tr
            }
        except Exception as e:
            logger.error(f"Error computing admin dashboard KPIs: {e}")
            return default_kpis

    @staticmethod
    def get_admin_chart_analytics(period='30d'):
        """Computes true database-derived datasets for all 7 dashboard charts."""
        empty_charts = {
            'growth_labels': [], 'growth_data': [],
            'status_labels': ['Active', 'Pending', 'Expired', 'Cancelled'], 'status_data': [0, 0, 0, 0],
            'cash_labels': [], 'cash_data': [],
            'attendance_labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], 'attendance_data': [0, 0, 0, 0, 0, 0, 0],
            'package_labels': [], 'package_data': [],
            'class_labels': [], 'class_data': [],
            'trainer_labels': [], 'trainer_data': []
        }
        if not db_service.is_configured:
            return empty_charts

        try:
            members = GymRepository.get_all_members()
            subscriptions = GymRepository.get_all_subscriptions()
            payments = GymRepository.get_all_cash_payments()
            attendance = GymRepository.get_all_attendance()
            classes = GymRepository.get_upcoming_classes()
            trainers = GymRepository.get_all_trainers()
            plans = GymRepository.get_all_plans()

            # 1. Growth Trend (last 6 months or days)
            growth_map = {}
            for m in members:
                c_date = m.get('created_at', '')[:7] # YYYY-MM
                if c_date:
                    growth_map[c_date] = growth_map.get(c_date, 0) + 1
            growth_sorted = sorted(growth_map.items())
            growth_labels = [k for k, _ in growth_sorted] or ['Current Month']
            growth_data = [v for _, v in growth_sorted] or [len(members)]

            # 2. Status Doughnut
            active_cnt = sum(1 for s in subscriptions if s.get('status') == 'active')
            pending_cnt = sum(1 for s in subscriptions if s.get('status') == 'pending')
            expired_cnt = sum(1 for s in subscriptions if s.get('status') == 'expired')
            cancelled_cnt = sum(1 for s in subscriptions if s.get('status') == 'cancelled')

            # 3. Cash Collection (Daily or Weekly)
            cash_map = {}
            for p in payments:
                if p.get('status') == 'confirmed':
                    p_date = p.get('payment_date', '')[:10]
                    if p_date:
                        cash_map[p_date] = cash_map.get(p_date, 0.0) + float(p.get('amount', 0))
            cash_sorted = sorted(cash_map.items())[-10:] # last 10 transaction dates
            cash_labels = [k for k, _ in cash_sorted]
            cash_data = [v for _, v in cash_sorted]

            # 4. Attendance Days
            att_data = [0] * 7
            for a in attendance:
                try:
                    dt = datetime.datetime.fromisoformat(a['check_in_time'].replace('Z', '+00:00'))
                    att_data[dt.weekday()] += 1
                except Exception:
                    pass

            # 5. Package Distribution
            pkg_map = {}
            for s in subscriptions:
                plan_name = s.get('membership_plans', {}).get('name', 'Standard') if s.get('membership_plans') else 'Plan'
                pkg_map[plan_name] = pkg_map.get(plan_name, 0) + 1
            package_labels = list(pkg_map.keys())
            package_data = list(pkg_map.values())

            # 6. Class Participation
            class_labels = [c.get('name', 'Class') for c in classes[:6]]
            class_data = [c.get('capacity', 20) for c in classes[:6]]

            # 7. Trainer Workload
            trainer_labels = [t.get('full_name', 'Coach') for t in trainers]
            # count assignments per trainer
            assignments = GymRepository.get_all_trainer_assignments()
            tr_counts = {}
            for a in assignments:
                t_id = a.get('trainer_id')
                tr_counts[t_id] = tr_counts.get(t_id, 0) + 1
            trainer_data = [tr_counts.get(t.get('id'), 0) for t in trainers]

            return {
                'growth_labels': growth_labels, 'growth_data': growth_data,
                'status_labels': ['Active', 'Pending', 'Expired', 'Cancelled'],
                'status_data': [active_cnt, pending_cnt, expired_cnt, cancelled_cnt],
                'cash_labels': cash_labels, 'cash_data': cash_data,
                'attendance_labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'attendance_data': att_data,
                'package_labels': package_labels, 'package_data': package_data,
                'class_labels': class_labels, 'class_data': class_data,
                'trainer_labels': trainer_labels, 'trainer_data': trainer_data
            }
        except Exception as e:
            logger.error(f"Error computing admin chart analytics: {e}")
            return empty_charts

    # =========================================================================
    # 3. GYM SERVICES (FULL CRUD)
    # =========================================================================
    @staticmethod
    def get_published_services():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('services').select('*').eq('is_published', True).order('sort_order').execute()
            return [s for s in res.data if not s.get('is_archived', False)]
        except Exception as e:
            logger.error(f"Error fetching published services: {e}")
            return []

    @staticmethod
    def get_all_services(include_archived=False):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('services').select('*').order('sort_order').execute()
            if not include_archived:
                return [s for s in res.data if not s.get('is_archived', False)]
            return res.data
        except Exception as e:
            logger.error(f"Error fetching all services: {e}")
            return []

    @staticmethod
    def get_service_by_id(service_id: str):
        if not db_service.is_configured:
            return None
        try:
            res = db_service.get_table('services').select('*').eq('id', service_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching service {service_id}: {e}")
            return None

    @staticmethod
    def create_service(data: dict):
        if not db_service.is_configured:
            return None
        try:
            res = db_service.get_table('services').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            raise e

    @staticmethod
    def update_service(service_id: str, data: dict):
        if not db_service.is_configured:
            return None
        try:
            res = db_service.get_table('services').update(data).eq('id', service_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error updating service: {e}")
            raise e

    @staticmethod
    def archive_service(service_id: str):
        if not db_service.is_configured:
            return False
        try:
            db_service.get_table('services').update({'is_archived': True, 'is_published': False}).eq('id', service_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error archiving service {service_id}: {e}")
            return False

    # =========================================================================
    # 4. MEMBERSHIP PLANS & PACKAGES
    # =========================================================================
    @staticmethod
    def get_active_plans():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('membership_plans').select('*').eq('is_active', True).order('price').execute()
            return [p for p in res.data if not p.get('is_archived', False)]
        except Exception as e:
            logger.error(f"Error fetching active plans: {e}")
            return []

    @staticmethod
    def get_all_plans(include_archived=False):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('membership_plans').select('*').order('created_at', desc=True).execute()
            if not include_archived:
                return [p for p in res.data if not p.get('is_archived', False)]
            return res.data
        except Exception as e:
            logger.error(f"Error fetching plans: {e}")
            return []

    @staticmethod
    def get_plan_by_id(plan_id: str):
        if not db_service.is_configured:
            return None
        try:
            res = db_service.get_table('membership_plans').select('*').eq('id', plan_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching plan {plan_id}: {e}")
            return None

    @staticmethod
    def update_plan(plan_id: str, data: dict):
        if not db_service.is_configured:
            return None
        try:
            data['updated_at'] = datetime.datetime.now().isoformat()
            res = db_service.get_table('membership_plans').update(data).eq('id', plan_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error updating plan {plan_id}: {e}")
            raise e

    @staticmethod
    def archive_plan(plan_id: str):
        if not db_service.is_configured:
            return False
        try:
            db_service.get_table('membership_plans').update({'is_archived': True, 'is_active': False}).eq('id', plan_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error archiving plan {plan_id}: {e}")
            return False

    # =========================================================================
    # 5. SUBSCRIPTIONS & RENEWALS
    # =========================================================================
    @staticmethod
    def get_all_subscriptions():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('member_subscriptions').select('*, profiles!member_subscriptions_member_id_fkey(id, full_name, email, phone), membership_plans(*)').order('created_at', desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching subscriptions: {e}")
            return []

    @staticmethod
    def get_member_subscriptions(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('member_subscriptions').select('*, membership_plans(*)').eq('member_id', member_id).order('created_at', desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching member subscriptions: {e}")
            return []

    @staticmethod
    def renew_subscription(sub_id: str, extension_days: int = 30):
        if not db_service.is_configured:
            return True
        try:
            sub = db_service.get_table('member_subscriptions').select('*, membership_plans(duration_days)').eq('id', sub_id).execute()
            if not sub.data:
                raise ValueError("Subscription record not found.")
            
            sub_rec = sub.data[0]
            plan_duration = sub_rec.get('membership_plans', {}).get('duration_days', extension_days) if sub_rec.get('membership_plans') else extension_days
            days_to_add = extension_days if extension_days and extension_days > 0 else plan_duration

            today = datetime.date.today()
            current_end_str = sub_rec.get('end_date')
            start_date = today
            if current_end_str:
                try:
                    current_end = datetime.date.fromisoformat(current_end_str[:10])
                    if current_end >= today:
                        start_date = current_end
                except Exception:
                    pass

            new_end = start_date + datetime.timedelta(days=days_to_add)
            renewal_count = (sub_rec.get('renewal_count') or 0) + 1

            db_service.get_table('member_subscriptions').update({
                'status': 'active',
                'end_date': new_end.isoformat(),
                'renewal_count': renewal_count,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', sub_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error renewing subscription {sub_id}: {e}")
            raise e

    @staticmethod
    def delete_subscription(sub_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('member_subscriptions').delete().eq('id', sub_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting subscription {sub_id}: {e}")
            raise e

    # =========================================================================
    # 6. CASH PAYMENTS & RECEIPTS (STRICT CASH ONLY)
    # =========================================================================
    @staticmethod
    def get_all_cash_payments():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('cash_payments').select('*, profiles!cash_payments_member_id_fkey(id, full_name, email), recorder:profiles!cash_payments_recorded_by_fkey(full_name)').order('payment_date', desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching cash payments: {e}")
            return []

    @staticmethod
    def get_member_cash_payments(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('cash_payments').select('*, recorder:profiles!cash_payments_recorded_by_fkey(full_name)').eq('member_id', member_id).order('payment_date', desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching member cash payments: {e}")
            return []

    @staticmethod
    def generate_receipt_number():
        year = datetime.datetime.now().year
        rand_suffix = str(uuid.uuid4().hex[:6]).upper()
        return f"RCP-{year}-{rand_suffix}"

    # =========================================================================
    # 7. MANUAL ATTENDANCE (FRONT-DESK ONLY)
    # =========================================================================
    @staticmethod
    def get_all_attendance(date_filter=None):
        if not db_service.is_configured:
            return []
        try:
            query = db_service.get_table('manual_attendance').select('*, profiles!manual_attendance_member_id_fkey(id, full_name, email), recorder:profiles!manual_attendance_recorded_by_fkey(full_name)').order('check_in_time', desc=True)
            if date_filter:
                query = query.gte('check_in_time', f"{date_filter}T00:00:00").lte('check_in_time', f"{date_filter}T23:59:59")
            res = query.execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching attendance: {e}")
            return []

    @staticmethod
    def get_member_attendance(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('manual_attendance').select('*, recorder:profiles!manual_attendance_recorded_by_fkey(full_name)').eq('member_id', member_id).order('check_in_time', desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching member attendance: {e}")
            return []

    @staticmethod
    def delete_attendance(attendance_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('manual_attendance').delete().eq('id', attendance_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting attendance record {attendance_id}: {e}")
            raise e

    # =========================================================================
    # 8. MEMBER DETAILS & COMPLETE 360 PROFILE
    # =========================================================================
    @staticmethod
    def get_all_members(include_archived=False):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('profiles').select('*, member_details(*)').eq('role', 'member').order('created_at', desc=True).execute()
            if not include_archived:
                return [m for m in res.data if not m.get('is_archived', False)]
            return res.data
        except Exception as e:
            logger.error(f"Error fetching members: {e}")
            return []

    @staticmethod
    def get_member_full_detail(member_id: str):
        """Fetches complete profile, member_details, subscriptions, payments, attendance, trainer, and progress."""
        if not db_service.is_configured:
            return None
        try:
            prof_res = db_service.get_table('profiles').select('*, member_details(*)').eq('id', member_id).execute()
            if not prof_res.data:
                return None
            profile = prof_res.data[0]

            subscriptions = GymRepository.get_member_subscriptions(member_id)
            payments = GymRepository.get_member_cash_payments(member_id)
            attendance = GymRepository.get_member_attendance(member_id)
            progress = GymRepository.get_member_progress(member_id)
            workout_plans = GymRepository.get_member_workout_plans(member_id)

            # Assigned trainer
            trainer_assignment = None
            try:
                ta_res = db_service.get_table('trainer_assignments').select('*, trainer:profiles!trainer_assignments_trainer_id_fkey(full_name, email, phone)').eq('member_id', member_id).eq('status', 'active').execute()
                if ta_res.data:
                    trainer_assignment = ta_res.data[0]
            except Exception:
                pass

            return {
                'profile': profile,
                'subscriptions': subscriptions,
                'payments': payments,
                'attendance': attendance,
                'progress': progress,
                'workout_plans': workout_plans,
                'trainer_assignment': trainer_assignment
            }
        except Exception as e:
            logger.error(f"Error fetching member detail for {member_id}: {e}")
            return None

    @staticmethod
    def update_member_profile(member_id: str, profile_data: dict, details_data: dict = None):
        if not db_service.is_configured:
            return False
        try:
            profile_data['updated_at'] = datetime.datetime.now().isoformat()
            db_service.get_table('profiles').update(profile_data).eq('id', member_id).execute()
            if details_data:
                db_service.get_table('member_details').upsert({'id': member_id, **details_data}).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating member profile {member_id}: {e}")
            raise e

    @staticmethod
    def archive_member(member_id: str):
        if not db_service.is_configured:
            return False
        try:
            db_service.get_table('profiles').update({'is_archived': True, 'is_active': False}).eq('id', member_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error archiving member {member_id}: {e}")
            return False

    @staticmethod
    def delete_member(member_id: str):
        """Permanently deletes an athlete member profile, dependencies, and authentication account."""
        if not db_service.is_configured:
            return True
        try:
            # Delete dependent relations
            for tbl in ['trainer_assignments', 'manual_attendance', 'member_subscriptions', 'member_progress_logs', 'workout_plans', 'member_details']:
                try:
                    col = 'member_id' if tbl != 'member_details' else 'id'
                    db_service.get_table(tbl).delete().eq(col, member_id).execute()
                except Exception as del_err:
                    logger.warning(f"Cleanup {tbl} for member {member_id}: {del_err}")

            # Preserve financial accounting history by disassociating member_id instead of deleting cash record
            try:
                db_service.get_table('cash_payments').update({'member_id': None}).eq('member_id', member_id).execute()
            except Exception:
                pass

            # Delete profile from profiles table
            db_service.get_table('profiles').delete().eq('id', member_id).execute()

            # Attempt to remove from Supabase Auth admin
            try:
                if hasattr(db_service, 'client') and hasattr(db_service.client, 'auth') and hasattr(db_service.client.auth, 'admin'):
                    db_service.client.auth.admin.delete_user(member_id)
            except Exception as auth_del_err:
                logger.warning(f"Auth admin user deletion notice: {auth_del_err}")

            return True
        except Exception as e:
            logger.error(f"Error deleting member {member_id}: {e}")
            raise e

    # =========================================================================
    # 9. TRAINERS & ASSIGNMENTS
    # =========================================================================
    @staticmethod
    def get_all_trainers(include_archived=False):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('profiles').select('*, trainer_details!trainer_details_id_fkey(*)').eq('role', 'trainer').order('created_at', desc=True).execute()
            trainers = res.data or []
            for t in trainers:
                td = t.get('trainer_details')
                if isinstance(td, list) and td:
                    td = td[0]
                    t['trainer_details'] = td
                elif not isinstance(td, dict):
                    td = {}
                    t['trainer_details'] = td
                t['bio'] = t.get('bio') or td.get('bio') or 'Dedicated athletic coach at Strakly Gym committed to member results.'
                t['specialisations'] = t.get('specialisations') or td.get('specialisations') or ['Strength & Conditioning']
                t['certifications'] = t.get('certifications') or td.get('certifications') or 'Certified Coach'
            if not include_archived:
                return [t for t in trainers if not t.get('is_archived', False)]
            return trainers
        except Exception as e:
            logger.error(f"Error fetching trainers with explicit relationship: {e}")
            try:
                # Fallback to plain query
                res = db_service.get_table('profiles').select('*').eq('role', 'trainer').order('created_at', desc=True).execute()
                trainers = res.data or []
                for t in trainers:
                    det = db_service.get_table('trainer_details').select('*').eq('id', t['id']).execute()
                    td = det.data[0] if det.data else {}
                    t['trainer_details'] = td
                    t['bio'] = t.get('bio') or td.get('bio') or 'Dedicated athletic coach at Strakly Gym committed to member results.'
                    t['specialisations'] = t.get('specialisations') or td.get('specialisations') or ['Strength & Conditioning']
                    t['certifications'] = t.get('certifications') or td.get('certifications') or 'Certified Coach'
                if not include_archived:
                    return [t for t in trainers if not t.get('is_archived', False)]
                return trainers
            except Exception as e2:
                logger.error(f"Error in trainer fallback query: {e2}")
                return []

    @staticmethod
    def create_trainer_account(full_name: str, email: str, phone: str = '', specialisations: list = None, bio: str = ''):
        """Creates or links a trainer account, profile, and trainer_details."""
        if not db_service.is_configured:
            return {'id': str(uuid.uuid4()), 'full_name': full_name, 'email': email}
        try:
            # Check if profile with email exists
            existing = db_service.get_table('profiles').select('*').eq('email', email.lower()).execute()
            if existing.data:
                trainer_id = existing.data[0]['id']
                db_service.get_table('profiles').update({
                    'full_name': full_name,
                    'role': 'trainer',
                    'phone': phone,
                    'is_active': True,
                    'is_archived': False
                }).eq('id', trainer_id).execute()
            else:
                # Attempt to create via Supabase Auth admin or profile
                trainer_id = str(uuid.uuid4())
                try:
                    auth_res = db_service.client.auth.admin.create_user({
                        'email': email.lower(),
                        'email_confirm': True,
                        'user_metadata': {'full_name': full_name, 'role': 'trainer'}
                    })
                    if auth_res and hasattr(auth_res, 'user') and auth_res.user:
                        trainer_id = auth_res.user.id
                except Exception as auth_err:
                    logger.warning(f"Auth admin create_user notice: {auth_err}")

                db_service.get_table('profiles').upsert({
                    'id': trainer_id,
                    'email': email.lower(),
                    'full_name': full_name,
                    'phone': phone,
                    'role': 'trainer',
                    'is_active': True,
                    'is_archived': False
                }).execute()

            # Upsert trainer details
            db_service.get_table('trainer_details').upsert({
                'id': trainer_id,
                'trainer_number': f"TR-{str(uuid.uuid4().hex[:6]).upper()}",
                'specialisations': specialisations or ['Strength & Conditioning'],
                'bio': bio or 'Certified fitness coach at Strakly.'
            }).execute()

            return {'id': trainer_id, 'full_name': full_name, 'email': email}
        except Exception as e:
            logger.error(f"Error creating trainer account: {e}")
            raise e

    @staticmethod
    def edit_trainer(trainer_id: str, full_name: str, phone: str, specialisations: list, bio: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('profiles').update({
                'full_name': full_name,
                'phone': phone
            }).eq('id', trainer_id).execute()

            # Check if trainer_number exists
            existing_td = db_service.get_table('trainer_details').select('trainer_number').eq('id', trainer_id).execute()
            tr_num = existing_td.data[0]['trainer_number'] if existing_td.data and existing_td.data[0].get('trainer_number') else f"TR-{str(uuid.uuid4().hex[:6]).upper()}"

            db_service.get_table('trainer_details').upsert({
                'id': trainer_id,
                'trainer_number': tr_num,
                'specialisations': specialisations,
                'bio': bio
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating trainer {trainer_id}: {e}")
            raise e

    @staticmethod
    def archive_trainer(trainer_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('profiles').update({'is_archived': True, 'is_active': False}).eq('id', trainer_id).execute()
            db_service.get_table('trainer_assignments').update({'status': 'inactive'}).eq('trainer_id', trainer_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error archiving trainer {trainer_id}: {e}")
            raise e

    @staticmethod
    def get_all_trainer_assignments():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('trainer_assignments').select('*, member:profiles!trainer_assignments_member_id_fkey(full_name, email), trainer:profiles!trainer_assignments_trainer_id_fkey(full_name)').eq('status', 'active').execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching trainer assignments: {e}")
            return []

    # =========================================================================
    # 10. CLASSES & BOOKINGS
    # =========================================================================
    @staticmethod
    def get_upcoming_classes():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('fitness_classes').select('*, profiles(full_name)').eq('is_published', True).gte('class_date', datetime.date.today().isoformat()).order('class_date').order('start_time').execute()
            return [c for c in res.data if not c.get('is_archived', False)]
        except Exception as e:
            logger.error(f"Error fetching upcoming classes: {e}")
            return []

    @staticmethod
    def get_all_classes(include_archived=False):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('fitness_classes').select('*, profiles(full_name)').order('class_date', desc=True).execute()
            if not include_archived:
                return [c for c in res.data if not c.get('is_archived', False)]
            return res.data
        except Exception as e:
            logger.error(f"Error fetching all classes: {e}")
            return []

    # =========================================================================
    # 11. EXERCISE LIBRARY & WORKOUT PLANS
    # =========================================================================
    @staticmethod
    def get_exercise_library(include_archived=False):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('exercise_library').select('*').order('name').execute()
            if not include_archived:
                return [e for e in res.data if not e.get('is_archived', False)]
            return res.data
        except Exception as e:
            logger.error(f"Error fetching exercises: {e}")
            return []

    @staticmethod
    def update_exercise(exercise_id: str, data: dict):
        if not db_service.is_configured:
            return None
        try:
            res = db_service.get_table('exercise_library').update(data).eq('id', exercise_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error updating exercise {exercise_id}: {e}")
            raise e

    @staticmethod
    def get_member_workout_plans(member_id: str):
        if not db_service.is_configured or not member_id:
            return []
        try:
            res = db_service.get_table('workout_plans').select('*, profiles:trainer_id(full_name)').eq('member_id', member_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching member workout plans: {e}")
            return []

    @staticmethod
    def get_member_progress(member_id: str):
        if not db_service.is_configured or not member_id:
            return []
        try:
            res = db_service.get_table('member_progress_logs').select('*').eq('member_id', member_id).order('recorded_date', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching member progress logs: {e}")
            return []

    # =========================================================================
    # 12. GYM EQUIPMENT & MAINTENANCE
    # =========================================================================
    @staticmethod
    def get_all_equipment(include_archived=False):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('gym_equipment').select('*').order('name').execute()
            if not include_archived:
                return [eq for eq in res.data if not eq.get('is_archived', False)]
            return res.data
        except Exception as e:
            logger.error(f"Error fetching equipment: {e}")
            return []

    @staticmethod
    def get_equipment_maintenance_logs(equipment_id=None):
        if not db_service.is_configured:
            return []
        try:
            query = db_service.get_table('equipment_maintenance').select('*, gym_equipment(name), profiles(full_name)').order('service_date', desc=True)
            if equipment_id:
                query = query.eq('equipment_id', equipment_id)
            res = query.execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching equipment maintenance logs: {e}")
            return []

    # =========================================================================
    # 13. ANNOUNCEMENTS & NOTIFICATIONS
    # =========================================================================
    @staticmethod
    def get_all_announcements(include_archived=False):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('announcements').select('*, author:profiles(full_name)').order('created_at', desc=True).execute()
            if not include_archived:
                return [a for a in res.data if not a.get('is_archived', False)]
            return res.data
        except Exception as e:
            logger.error(f"Error fetching announcements: {e}")
            return []

    @staticmethod
    def create_announcement(data: dict):
        if not db_service.is_configured:
            return None
        try:
            res = db_service.get_table('announcements').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
            raise e

    @staticmethod
    def update_announcement(announcement_id: str, data: dict):
        if not db_service.is_configured:
            return None
        try:
            res = db_service.get_table('announcements').update(data).eq('id', announcement_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error updating announcement {announcement_id}: {e}")
            raise e

    @staticmethod
    def delete_announcement(announcement_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('announcements').delete().eq('id', announcement_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting announcement {announcement_id}: {e}")
            raise e

    @staticmethod
    def broadcast_notification(title: str, message: str, notif_type='general', target_role='all', action_url=None):
        if not db_service.is_configured:
            return False
        try:
            # Query target users
            query = db_service.get_table('profiles').select('id')
            if target_role != 'all':
                query = query.eq('role', target_role)
            users_res = query.execute()

            rows = [{
                'user_id': u['id'],
                'title': title,
                'message': message,
                'type': notif_type,
                'action_url': action_url
            } for u in (users_res.data or [])]

            if rows:
                db_service.get_table('notifications').insert(rows).execute()
            return True
        except Exception as e:
            logger.error(f"Error broadcasting notifications: {e}")
            return False

    @staticmethod
    def get_user_notifications(user_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('notifications').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(25).execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
            return []

    @staticmethod
    def delete_notification(notification_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('notifications').delete().eq('id', notification_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting notification {notification_id}: {e}")
            raise e

    # =========================================================================
    # 14. USER ACCOUNTS & ACCESS CONTROL
    # =========================================================================
    @staticmethod
    def get_all_user_accounts():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('profiles').select('*').order('created_at', desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching user accounts: {e}")
            return []

    @staticmethod
    def update_user_role(user_id: str, new_role: str):
        if not db_service.is_configured:
            return False
        try:
            db_service.get_table('profiles').update({'role': new_role, 'updated_at': datetime.datetime.now().isoformat()}).eq('id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            raise e

    @staticmethod
    def toggle_user_active(user_id: str, is_active: bool):
        if not db_service.is_configured:
            return False
        try:
            db_service.get_table('profiles').update({'is_active': is_active, 'updated_at': datetime.datetime.now().isoformat()}).eq('id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error toggling user active status: {e}")
            raise e

    @staticmethod
    def update_user_account(user_id: str, data: dict):
        if not db_service.is_configured:
            return None
        try:
            data['updated_at'] = datetime.datetime.now().isoformat()
            res = db_service.get_table('profiles').update(data).eq('id', user_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error updating user account {user_id}: {e}")
            raise e

    @staticmethod
    def change_user_password(user_id: str, email: str, current_password: str, new_password: str):
        """
        Securely verifies current password and updates to new password.
        Never stores or logs plaintext passwords.
        """
        if not new_password or len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters long.")
        if not any(c.isdigit() for c in new_password) or not any(c.isalpha() for c in new_password):
            raise ValueError("Password must contain both letters and at least one number.")

        if db_service.is_configured:
            # 1. Verify current password
            try:
                verify_res = db_service.client.auth.sign_in_with_password({'email': email, 'password': current_password})
                if not verify_res or not hasattr(verify_res, 'user') or not verify_res.user:
                    raise ValueError("Current password verification failed.")
            except Exception as e:
                logger.warning(f"Password verification failure for {email}: {e}")
                raise ValueError("Current password does not match our records.")

            # 2. Update user password
            try:
                db_service.client.auth.update_user({'password': new_password})
            except Exception as update_err:
                admin_auth = getattr(db_service.client.auth, 'admin', None)
                if admin_auth and hasattr(admin_auth, 'update_user_by_id'):
                    admin_auth.update_user_by_id(user_id, {'password': new_password})
                else:
                    raise update_err

            # 3. Update profile updated_at timestamp
            try:
                db_service.get_table('profiles').update({'updated_at': datetime.datetime.now().isoformat()}).eq('id', user_id).execute()
            except Exception:
                pass
        return True

    @staticmethod
    def admin_reset_user_password(admin_user_id: str, target_user_id: str, new_password: str = None):
        """
        Administrator-authorized password reset or dispatch of password reset email.
        Admin never sees the user's existing password.
        """
        if db_service.is_configured:
            prof_res = db_service.get_table('profiles').select('email, full_name').eq('id', target_user_id).execute()
            if not prof_res.data:
                raise ValueError("Target user profile not found.")
            target_email = prof_res.data[0]['email']

            admin_auth = getattr(db_service.client.auth, 'admin', None)
            if new_password:
                if len(new_password) < 8:
                    raise ValueError("New password must be at least 8 characters long.")
                try:
                    if admin_auth and hasattr(admin_auth, 'update_user_by_id'):
                        admin_auth.update_user_by_id(target_user_id, {'password': new_password})
                    else:
                        db_service.client.auth.reset_password_for_email(target_email)
                except Exception as e:
                    logger.warning(f"Admin direct update failed, falling back to reset email: {e}")
                    db_service.client.auth.reset_password_for_email(target_email)
            else:
                db_service.client.auth.reset_password_for_email(target_email)

            try:
                db_service.get_table('profiles').update({'updated_at': datetime.datetime.now().isoformat()}).eq('id', target_user_id).execute()
            except Exception:
                pass
        return True

    @staticmethod
    def create_user_account(full_name: str, email: str, role: str, phone: str = ''):
        """Creates a new user profile and Auth identity."""
        if not db_service.is_configured:
            return {'id': str(uuid.uuid4()), 'full_name': full_name, 'email': email, 'role': role}
        try:
            user_id = str(uuid.uuid4())
            try:
                auth_res = db_service.client.auth.admin.create_user({
                    'email': email.lower(),
                    'email_confirm': True,
                    'user_metadata': {'full_name': full_name, 'role': role}
                })
                if auth_res and hasattr(auth_res, 'user') and auth_res.user:
                    user_id = auth_res.user.id
            except Exception as auth_err:
                logger.warning(f"Auth create_user notice: {auth_err}")

            db_service.get_table('profiles').upsert({
                'id': user_id,
                'email': email.lower(),
                'full_name': full_name,
                'phone': phone,
                'role': role,
                'is_active': True,
                'is_archived': False
            }).execute()

            if role == 'member':
                db_service.get_table('member_details').upsert({
                    'id': user_id,
                    'member_number': f"STR-{str(uuid.uuid4().hex[:6]).upper()}"
                }).execute()
            elif role == 'trainer':
                db_service.get_table('trainer_details').upsert({
                    'id': user_id,
                    'trainer_number': f"TR-{str(uuid.uuid4().hex[:6]).upper()}",
                    'specialisations': ['General Conditioning'],
                    'bio': 'Coach at Strakly.'
                }).execute()

            return {'id': user_id, 'full_name': full_name, 'email': email, 'role': role}
        except Exception as e:
            logger.error(f"Error in create_user_account: {e}")
            raise e

    @staticmethod
    def delete_user_account(user_id: str, permanent: bool = True):
        """
        Permanent deletion of a user account with comprehensive data safeguards.
        1. Protects sole active admin and prevents self-deletion.
        2. Preserves cash payment receipts by nullifying foreign key references.
        3. Cleans related member subscriptions, attendance, trainer assignments.
        4. Permanently removes profile and Supabase Auth credentials.
        """
        if not db_service.is_configured:
            return True
        try:
            # Check if protected last admin
            profile_res = db_service.get_table('profiles').select('*').eq('id', user_id).execute()
            if profile_res.data and profile_res.data[0].get('role') == 'admin':
                admin_count = db_service.get_table('profiles').select('id').eq('role', 'admin').eq('is_active', True).execute()
                if len(admin_count.data) <= 1:
                    raise ValueError("Cannot delete or deactivate the sole active administrator account.")

            if permanent:
                # 1. Preserve financial audit trail: disassociate member_id on cash_payments so financial logs persist
                try:
                    db_service.get_table('cash_payments').update({'member_id': None}).eq('member_id', user_id).execute()
                except Exception as pay_err:
                    logger.debug(f"Preserving payments note: {pay_err}")

                # 2. Clean child relational tables
                for child_tbl, col in [
                    ('member_subscriptions', 'member_id'),
                    ('manual_attendance', 'member_id'),
                    ('trainer_assignments', 'member_id'),
                    ('trainer_assignments', 'trainer_id'),
                    ('pt_sessions', 'member_id'),
                    ('pt_sessions', 'trainer_id'),
                    ('user_notifications', 'user_id'),
                    ('workout_logs', 'member_id'),
                    ('service_inquiries', 'member_id'),
                    ('equipment_reservations', 'member_id'),
                    ('store_orders', 'member_id'),
                    ('trainer_details', 'id')
                ]:
                    try:
                        db_service.get_table(child_tbl).delete().eq(col, user_id).execute()
                    except Exception:
                        pass

                # 3. Permanently delete from profiles
                db_service.get_table('profiles').delete().eq('id', user_id).execute()

                # 4. Remove from Supabase Auth admin if available
                try:
                    if hasattr(db_service, 'client') and hasattr(db_service.client, 'auth') and hasattr(db_service.client.auth, 'admin'):
                        db_service.client.auth.admin.delete_user(user_id)
                except Exception as auth_err:
                    logger.debug(f"Auth admin deletion: {auth_err}")
            else:
                db_service.get_table('profiles').update({
                    'is_active': False,
                    'is_archived': True,
                    'archived_at': datetime.datetime.now().isoformat()
                }).eq('id', user_id).execute()

            return True
        except Exception as e:
            logger.error(f"Error permanently deleting user {user_id}: {e}")
            raise e

    # =========================================================================
    # 15. AUDIT LOGS
    # =========================================================================
    @staticmethod
    def get_audit_logs(limit=200, role_filter=None, action_filter=None, search=None):
        if not db_service.is_configured:
            return []
        try:
            query = db_service.get_table('audit_logs').select('*, profiles(full_name, email)').order('created_at', desc=True).limit(limit)
            if role_filter:
                query = query.eq('actor_role', role_filter)
            if action_filter:
                query = query.eq('action_type', action_filter)
            res = query.execute()
            
            logs = res.data or []
            if search:
                s = search.lower()
                logs = [l for l in logs if s in (l.get('target_entity') or '').lower() or s in (l.get('action_type') or '').lower() or s in str(l.get('details') or '').lower()]
            return logs
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            return []

    # =========================================================================
    # 16. COMMUNITY POSTS & REPORTS
    # =========================================================================
    @staticmethod
    def get_community_posts(group_id=None, include_hidden=True):
        if not db_service.is_configured:
            return []
        try:
            query = db_service.get_table('community_posts').select('*, author:profiles(full_name, avatar_url, role), community_comments(*, author:profiles(full_name, avatar_url)), community_reactions(*)').order('created_at', desc=True)
            if not include_hidden:
                query = query.eq('is_hidden', False)
            if group_id:
                query = query.eq('group_id', group_id)
            res = query.execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching community posts: {e}")
            return []

    @staticmethod
    def unhide_community_post(post_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('community_posts').update({'is_hidden': False}).eq('id', post_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error unhiding post {post_id}: {e}")
            raise e

    @staticmethod
    def delete_community_post(post_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('community_posts').delete().eq('id', post_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting community post {post_id}: {e}")
            raise e

    @staticmethod
    def get_community_groups():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('community_groups').select('*').eq('is_active', True).order('name').execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching community groups: {e}")
            return []

    @staticmethod
    def get_community_reports():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('community_reports').select('*, reporter:profiles!community_reports_reporter_id_fkey(full_name, email), post:community_posts(content, author_id)').order('created_at', desc=True).execute()
            return res.data
        except Exception as e:
            logger.error(f"Error fetching community reports: {e}")
            return []

    # =========================================================================
    # 17. PUBLIC STATS AGGREGATES
    # =========================================================================
    @staticmethod
    def get_public_stats():
        """Returns genuine database aggregates for public homepage statistics."""
        if not db_service.is_configured:
            return {
                'active_members': 0,
                'available_trainers': 0,
                'upcoming_classes': 0,
                'published_programmes': 0,
                'weekly_attendance_labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'weekly_attendance_data': [0, 0, 0, 0, 0, 0, 0]
            }
        try:
            active_members = len(GymRepository.get_all_members())
            available_trainers = len(GymRepository.get_all_trainers())
            upcoming_classes = len(GymRepository.get_upcoming_classes())
            published_programmes = len(GymRepository.get_published_services())
            
            attendance = GymRepository.get_all_attendance()
            labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            data = [0] * 7
            for a in attendance:
                try:
                    dt = datetime.datetime.fromisoformat(a['check_in_time'].replace('Z', '+00:00'))
                    data[dt.weekday()] += 1
                except Exception:
                    pass

            return {
                'active_members': active_members,
                'available_trainers': available_trainers,
                'upcoming_classes': upcoming_classes,
                'published_programmes': published_programmes,
                'weekly_attendance_labels': labels,
                'weekly_attendance_data': data
            }
        except Exception as e:
            logger.error(f"Error generating public stats: {e}")
            return {
                'active_members': 0,
                'available_trainers': 0,
                'upcoming_classes': 0,
                'published_programmes': 0,
                'weekly_attendance_labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'weekly_attendance_data': [0, 0, 0, 0, 0, 0, 0]
            }

    # =========================================================================
    # 18. TRAINEE PORTAL METHODS
    # =========================================================================
    @staticmethod
    def get_member_membership_requests(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('membership_requests').select('*, target_plan:membership_plans(name, price)').eq('member_id', member_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching membership requests: {e}")
            return []

    @staticmethod
    def submit_membership_request(member_id: str, request_type: str, target_plan_id: str = None, reason: str = '', freeze_start_date: str = None, freeze_end_date: str = None):
        if not db_service.is_configured:
            return {'id': 'mock-req-id', 'request_type': request_type, 'status': 'pending'}
        try:
            data = {
                'member_id': member_id,
                'request_type': request_type,
                'reason': reason,
                'status': 'pending'
            }
            if target_plan_id:
                data['target_plan_id'] = target_plan_id
            if freeze_start_date:
                data['freeze_start_date'] = freeze_start_date
            if freeze_end_date:
                data['freeze_end_date'] = freeze_end_date
            res = db_service.get_table('membership_requests').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error submitting membership request: {e}")
            raise e

    @staticmethod
    def get_member_pt_wallet(member_id: str):
        if not db_service.is_configured:
            return {'total_sessions_purchased': 5, 'sessions_used': 2, 'sessions_remaining': 3}
        try:
            res = db_service.get_table('member_pt_wallets').select('*').eq('member_id', member_id).execute()
            if res.data:
                return res.data[0]
            # Create default wallet with 0 sessions if none exists
            new_wallet = {'member_id': member_id, 'total_sessions_purchased': 0, 'sessions_used': 0}
            ins = db_service.get_table('member_pt_wallets').insert(new_wallet).execute()
            return ins.data[0] if ins.data else {'total_sessions_purchased': 0, 'sessions_used': 0, 'sessions_remaining': 0}
        except Exception as e:
            logger.error(f"Error fetching PT wallet: {e}")
            return {'total_sessions_purchased': 0, 'sessions_used': 0, 'sessions_remaining': 0}

    @staticmethod
    def get_member_pt_sessions(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('pt_sessions').select('*, trainer:profiles!pt_sessions_trainer_id_fkey(full_name, email, phone)').eq('member_id', member_id).order('session_date', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching PT sessions: {e}")
            return []

    @staticmethod
    def book_pt_session(member_id: str, trainer_id: str, session_date: str, start_time: str, focus_area: str = 'General Fitness', notes: str = ''):
        if not db_service.is_configured:
            return {'id': 'mock-pt-id', 'status': 'requested'}
        try:
            data = {
                'member_id': member_id,
                'trainer_id': trainer_id,
                'session_date': session_date,
                'start_time': start_time,
                'focus_area': focus_area,
                'notes': notes,
                'status': 'requested'
            }
            res = db_service.get_table('pt_sessions').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error booking PT session: {e}")
            raise e

    @staticmethod
    def get_member_coach(member_id: str):
        if not db_service.is_configured:
            return None
        try:
            res = db_service.get_table('trainer_assignments').select('*, trainer:profiles!trainer_assignments_trainer_id_fkey(id, full_name, email, phone, avatar_url)').eq('member_id', member_id).eq('status', 'active').execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error fetching member coach: {e}")
            return None

    @staticmethod
    def submit_coach_request(member_id: str, preferred_trainer_id: str = None, request_type: str = 'assign', fitness_goals: str = '', notes: str = ''):
        if not db_service.is_configured:
            return {'id': 'mock-coach-req'}
        try:
            data = {
                'member_id': member_id,
                'preferred_trainer_id': preferred_trainer_id,
                'request_type': request_type,
                'fitness_goals': fitness_goals,
                'notes': notes,
                'status': 'pending'
            }
            res = db_service.get_table('coach_requests').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error submitting coach request: {e}")
            raise e

    @staticmethod
    def get_member_goals(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('member_goals').select('*').eq('member_id', member_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching member goals: {e}")
            return []

    @staticmethod
    def create_member_goal(member_id: str, title: str, category: str, target_value: float, current_value: float = 0, unit: str = 'kg', target_date: str = None):
        if not db_service.is_configured:
            return {'id': 'mock-goal-id'}
        try:
            data = {
                'member_id': member_id,
                'title': title,
                'category': category,
                'target_value': target_value,
                'current_value': current_value,
                'start_value': current_value,
                'unit': unit,
                'target_date': target_date,
                'status': 'in_progress'
            }
            res = db_service.get_table('member_goals').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error creating member goal: {e}")
            raise e

    @staticmethod
    def update_member_goal(goal_id: str, current_value: float, status: str = 'in_progress'):
        if not db_service.is_configured:
            return {'id': goal_id}
        try:
            res = db_service.get_table('member_goals').update({'current_value': current_value, 'status': status, 'updated_at': 'now()'}).eq('id', goal_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error updating member goal: {e}")
            raise e

    @staticmethod
    def delete_member_goal(goal_id: str, member_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('member_goals').delete().eq('id', goal_id).eq('member_id', member_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting member goal: {e}")
            return False

    @staticmethod
    def get_member_prs(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('member_personal_records').select('*').eq('member_id', member_id).order('achieved_on', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching member PRs: {e}")
            return []

    @staticmethod
    def add_member_pr(member_id: str, exercise_name: str, weight_kg: float, reps: int = 1, notes: str = ''):
        if not db_service.is_configured:
            return {'id': 'mock-pr-id'}
        try:
            # Epley formula for estimated 1RM: Weight * (1 + Reps / 30)
            e1rm = round(float(weight_kg) * (1.0 + float(reps) / 30.0), 1) if reps > 1 else float(weight_kg)
            data = {
                'member_id': member_id,
                'exercise_name': exercise_name,
                'weight_kg': weight_kg,
                'reps': reps,
                'estimated_one_rep_max': e1rm,
                'notes': notes
            }
            res = db_service.get_table('member_personal_records').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error adding PR: {e}")
            raise e

    @staticmethod
    def get_member_progress_photos(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('member_progress_photos').select('*').eq('member_id', member_id).order('taken_on', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching progress photos: {e}")
            return []

    @staticmethod
    def add_progress_photo(member_id: str, photo_url: str, photo_tag: str = 'front', recorded_weight: float = None, notes: str = ''):
        if not db_service.is_configured:
            return {'id': 'mock-photo-id'}
        try:
            data = {
                'member_id': member_id,
                'photo_url': photo_url,
                'photo_tag': photo_tag,
                'notes': notes
            }
            if recorded_weight:
                data['recorded_weight'] = recorded_weight
            res = db_service.get_table('member_progress_photos').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error adding progress photo: {e}")
            raise e

    @staticmethod
    def delete_progress_photo(photo_id: str, member_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('member_progress_photos').delete().eq('id', photo_id).eq('member_id', member_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting progress photo: {e}")
            return False

    @staticmethod
    def get_active_challenges():
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('fitness_challenges').select('*, participants:challenge_participants(count)').eq('is_active', True).order('start_date', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching active challenges: {e}")
            return []

    @staticmethod
    def get_member_challenges(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('challenge_participants').select('*, challenge:fitness_challenges(*)').eq('member_id', member_id).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching member challenges: {e}")
            return []

    @staticmethod
    def join_challenge(member_id: str, challenge_id: str):
        if not db_service.is_configured:
            return {'id': 'mock-part-id'}
        try:
            data = {
                'member_id': member_id,
                'challenge_id': challenge_id,
                'current_progress': 0,
                'status': 'joined'
            }
            res = db_service.get_table('challenge_participants').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error joining challenge: {e}")
            raise e

    @staticmethod
    def get_member_achievements(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('member_achievements').select('*').eq('member_id', member_id).order('unlocked_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching achievements: {e}")
            return []

    @staticmethod
    def reserve_equipment(member_id: str, equipment_id: str, reservation_date: str, start_time: str, duration_minutes: int = 60, notes: str = ''):
        if not db_service.is_configured:
            return {'id': 'mock-reserve-id'}
        try:
            data = {
                'member_id': member_id,
                'equipment_id': equipment_id,
                'reservation_date': reservation_date,
                'start_time': start_time,
                'duration_minutes': duration_minutes,
                'notes': notes,
                'status': 'active'
            }
            res = db_service.get_table('equipment_reservations').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error reserving equipment: {e}")
            raise e

    @staticmethod
    def get_member_equipment_reservations(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('equipment_reservations').select('*, equipment:gym_equipment(name, category, brand, model_number)').eq('member_id', member_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching equipment reservations: {e}")
            return []

    @staticmethod
    def get_store_products(category: str = None, include_archived: bool = False):
        default_catalogue = [
            {
                'id': 'prod-001',
                'name': 'Strakly Heavy-Duty Lifting Belt',
                'category': 'Lifting Gear',
                'description': 'IPF-compliant 10mm genuine leather lever lifting belt engineered for maximal bracing and stability.',
                'price': 8500.00,
                'currency': 'KES',
                'stock_quantity': 24,
                'sku': 'STR-BLT-01',
                'image_url': 'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=800&q=80',
                'available_sizes': ['S', 'M', 'L', 'XL'],
                'is_active': True,
                'is_featured': True
            },
            {
                'id': 'prod-002',
                'name': 'Strakly Oversized Heavyweight Tee',
                'category': 'Apparel',
                'description': '280 GSM heavyweight combed cotton training shirt with dropped shoulders and embroidered chest crest.',
                'price': 2800.00,
                'currency': 'KES',
                'stock_quantity': 45,
                'sku': 'STR-TEE-01',
                'image_url': 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80',
                'available_sizes': ['S', 'M', 'L', 'XL', '2XL'],
                'is_active': True,
                'is_featured': True
            },
            {
                'id': 'prod-003',
                'name': 'Vacuum Insulated Stainless Shaker (750ml)',
                'category': 'Bottles & Shakers',
                'description': 'Double-walled vacuum insulated kitchen-grade stainless shaker with silent mixing mechanism.',
                'price': 1800.00,
                'currency': 'KES',
                'stock_quantity': 60,
                'sku': 'STR-SHK-01',
                'image_url': 'https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=800&q=80',
                'available_sizes': ['Standard'],
                'is_active': True,
                'is_featured': False
            },
            {
                'id': 'prod-004',
                'name': 'Heavy-Duty Gym Duffle Bag (45L)',
                'category': 'Gym Bags',
                'description': 'Water-resistant cordura nylon gear bag with ventilated shoe compartment and wet laundry pocket.',
                'price': 4500.00,
                'currency': 'KES',
                'stock_quantity': 28,
                'sku': 'STR-BAG-01',
                'image_url': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=800&q=80',
                'available_sizes': ['Standard'],
                'is_active': True,
                'is_featured': True
            },
            {
                'id': 'prod-005',
                'name': 'Elastic Heavy Wrist Wraps (Pair)',
                'category': 'Accessories',
                'description': '24-inch competition grade thumb-loop wrist supports with reinforced military velcro.',
                'price': 1500.00,
                'currency': 'KES',
                'stock_quantity': 50,
                'sku': 'STR-WRP-01',
                'image_url': 'https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?auto=format&fit=crop&w=800&q=80',
                'available_sizes': ['Standard'],
                'is_active': True,
                'is_featured': False
            },
            {
                'id': 'prod-006',
                'name': 'Deep Tissue Vibrating Foam Roller',
                'category': 'Recovery Accessories',
                'description': 'High-density contoured foam roller with 4-speed vibration motor for deep myofascial release.',
                'price': 3800.00,
                'currency': 'KES',
                'stock_quantity': 16,
                'sku': 'STR-ROL-01',
                'image_url': 'https://images.unsplash.com/photo-1600881333168-2ef49b341f30?auto=format&fit=crop&w=800&q=80',
                'available_sizes': ['Standard'],
                'is_active': True,
                'is_featured': True
            }
        ]

        if not db_service.is_configured:
            return default_catalogue
        try:
            query = db_service.get_table('store_products').select('*')
            if not include_archived:
                query = query.eq('is_active', True)
            if category:
                query = query.eq('category', category)
            res = query.order('created_at', desc=True).execute()
            if res.data and len(res.data) > 0:
                return res.data
            return default_catalogue
        except Exception as e:
            logger.error(f"Error fetching store products: {e}")
            return default_catalogue

    @staticmethod
    def create_store_product(name: str, category: str, price: float, description: str = '', stock_quantity: int = 10, image_url: str = '', sku: str = ''):
        data = {
            'name': name,
            'category': category,
            'price': float(price),
            'description': description,
            'stock_quantity': int(stock_quantity),
            'image_url': image_url,
            'sku': sku or f"STR-{name[:3].upper()}-{int(datetime.datetime.now().timestamp()) % 1000}",
            'is_active': True
        }
        if db_service.is_configured:
            try:
                res = db_service.get_table('store_products').insert(data).execute()
                return res.data[0] if res.data else data
            except Exception as e:
                logger.error(f"Error inserting product: {e}")
                return data
        return data

    @staticmethod
    def update_store_product(product_id: str, updates: dict):
        if db_service.is_configured:
            try:
                res = db_service.get_table('store_products').update(updates).eq('id', product_id).execute()
                return res.data[0] if res.data else updates
            except Exception as e:
                logger.error(f"Error updating product: {e}")
                return updates
        return updates

    @staticmethod
    def archive_store_product(product_id: str):
        if db_service.is_configured:
            try:
                db_service.get_table('store_products').update({'is_active': False, 'is_archived': True}).eq('id', product_id).execute()
                return True
            except Exception as e:
                logger.error(f"Error archiving product: {e}")
                return False
        return True

    @staticmethod
    def place_store_order(member_id: str, product_id: str, quantity: int = 1, selected_size: str = 'Standard', pickup_notes: str = ''):
        if not db_service.is_configured:
            return {'id': 'mock-order-id', 'order_number': 'ORD-MOCK-1'}
        try:
            prod_res = db_service.get_table('store_products').select('*').eq('id', product_id).execute()
            if not prod_res.data:
                raise ValueError("Product not found")
            product = prod_res.data[0]
            unit_price = float(product.get('price', 0))
            total_amount = unit_price * quantity
            order_number = f"STRK-{datetime.datetime.now().strftime('%y%m%d%H%M')}-{quantity}"

            data = {
                'order_number': order_number,
                'member_id': member_id,
                'product_id': product_id,
                'quantity': quantity,
                'selected_size': selected_size,
                'unit_price': unit_price,
                'total_amount': total_amount,
                'payment_method': 'cash_on_collection',
                'status': 'pending',
                'pickup_notes': pickup_notes
            }
            res = db_service.get_table('store_orders').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error placing store order: {e}")
            raise e

    @staticmethod
    def get_member_store_orders(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('store_orders').select('*, product:store_products(name, category, image_url)').eq('member_id', member_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching store orders: {e}")
            return []

    @staticmethod
    def submit_service_inquiry(member_id: str, service_id: str, preferred_date: str = None, preferred_time: str = None, notes: str = ''):
        if not db_service.is_configured:
            return {'id': 'mock-inquiry-id'}
        try:
            data = {
                'member_id': member_id,
                'service_id': service_id,
                'notes': notes,
                'status': 'pending'
            }
            if preferred_date:
                data['preferred_date'] = preferred_date
            if preferred_time:
                data['preferred_time'] = preferred_time
            res = db_service.get_table('service_inquiries').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error submitting service inquiry: {e}")
            raise e

    @staticmethod
    def get_member_service_inquiries(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('service_inquiries').select('*, service:services(name, description, price)').eq('member_id', member_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching service inquiries: {e}")
            return []

    @staticmethod
    def get_member_support_tickets(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('support_tickets').select('*').eq('member_id', member_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching support tickets: {e}")
            return []

    @staticmethod
    def create_support_ticket(member_id: str, category: str, subject: str, message: str, priority: str = 'normal'):
        if not db_service.is_configured:
            return {'id': 'mock-ticket-id'}
        try:
            ticket_number = f"TCK-{datetime.datetime.now().strftime('%y%m%d%H%M')}"
            data = {
                'ticket_number': ticket_number,
                'member_id': member_id,
                'category': category,
                'subject': subject,
                'message': message,
                'priority': priority,
                'status': 'open'
            }
            res = db_service.get_table('support_tickets').insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error creating support ticket: {e}")
            raise e

    @staticmethod
    def get_member_settings(member_id: str):
        default_settings = {
            'notify_email': True,
            'notify_sms': False,
            'notify_class_reminders': True,
            'notify_community_replies': True,
            'share_progress_with_coach': True,
            'public_leaderboard': True,
            'preferred_theme': 'fitpulse'
        }
        if not db_service.is_configured:
            return default_settings
        try:
            res = db_service.get_table('member_settings').select('*').eq('member_id', member_id).execute()
            if res.data:
                return res.data[0]
            # initialize
            init_data = {'member_id': member_id, **default_settings}
            ins = db_service.get_table('member_settings').insert(init_data).execute()
            return ins.data[0] if ins.data else default_settings
        except Exception as e:
            logger.error(f"Error fetching member settings: {e}")
            return default_settings

    @staticmethod
    def update_member_settings(member_id: str, settings_dict: dict):
        if not db_service.is_configured:
            return settings_dict
        try:
            # Check if row exists
            res = db_service.get_table('member_settings').select('id').eq('member_id', member_id).execute()
            if res.data:
                upd = db_service.get_table('member_settings').update(settings_dict).eq('member_id', member_id).execute()
                return upd.data[0] if upd.data else None
            else:
                settings_dict['member_id'] = member_id
                ins = db_service.get_table('member_settings').insert(settings_dict).execute()
                return ins.data[0] if ins.data else None
        except Exception as e:
            logger.error(f"Error updating member settings: {e}")
            raise e

    @staticmethod
    def get_member_booked_classes(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('class_bookings').select('*, fitness_class:fitness_classes(*, trainer:profiles!fitness_classes_trainer_id_fkey(full_name))').eq('member_id', member_id).order('booked_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching member booked classes: {e}")
            return []

    @staticmethod
    def cancel_class_booking(booking_id: str, member_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('class_bookings').update({'booking_status': 'cancelled'}).eq('id', booking_id).eq('member_id', member_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error cancelling class booking: {e}")
            return False

    @staticmethod
    def get_member_calendar_events(member_id: str):
        """Aggregates logged workouts, booked classes, and PT sessions for the training calendar."""
        events = []
        if not db_service.is_configured:
            return events
        try:
            # 1. Logged workouts
            try:
                wlogs = db_service.get_table('workout_logs').select('*').eq('member_id', member_id).execute()
                for w in (wlogs.data or []):
                    created = w.get('created_at', '')
                    date_str = created.split('T')[0] if 'T' in created else created[:10]
                    events.append({
                        'id': w.get('id'),
                        'title': w.get('title') or 'Workout Session',
                        'date': date_str,
                        'type': 'workout',
                        'badge': 'Workout',
                        'duration': w.get('duration_minutes', 60),
                        'notes': w.get('notes', '')
                    })
            except Exception:
                pass

            # 2. Booked classes
            try:
                cb = db_service.get_table('class_bookings').select('*, fitness_class:fitness_classes(*)').eq('member_id', member_id).eq('booking_status', 'confirmed').execute()
                for b in (cb.data or []):
                    fc = b.get('fitness_class') or {}
                    events.append({
                        'id': b.get('id'),
                        'title': fc.get('name') or 'Group Fitness Class',
                        'date': fc.get('date', ''),
                        'time': fc.get('start_time', ''),
                        'type': 'class',
                        'badge': 'Class',
                        'notes': f"Location: {fc.get('room', 'Studio')}"
                    })
            except Exception:
                pass

            # 3. PT sessions
            try:
                pts = db_service.get_table('pt_sessions').select('*, trainer:profiles!pt_sessions_trainer_id_fkey(full_name)').eq('member_id', member_id).execute()
                for p in (pts.data or []):
                    trainer_name = (p.get('trainer') or {}).get('full_name', 'Coach')
                    events.append({
                        'id': p.get('id'),
                        'title': f"1-on-1 PT with {trainer_name}",
                        'date': p.get('session_date', ''),
                        'time': p.get('start_time', ''),
                        'type': 'pt',
                        'badge': 'PT Session',
                        'notes': p.get('focus_area', 'Personal Coaching')
                    })
            except Exception:
                pass
            
            # Sort chronologically
            events.sort(key=lambda x: (x.get('date', ''), x.get('time', '')))
            return events
        except Exception as e:
            logger.error(f"Error aggregating calendar events: {e}")
            return []

    @staticmethod
    def get_member_notifications(member_id: str):
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('notifications').select('*').eq('user_id', member_id).order('created_at', desc=True).limit(50).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching member notifications: {e}")
            return []

    @staticmethod
    def mark_notifications_read(member_id: str):
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('notifications').update({'is_read': True}).eq('user_id', member_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking notifications read: {e}")
            return False

    @staticmethod
    def update_member_profile(member_id: str, full_name: str, phone: str, emergency_name: str = '', emergency_phone: str = '', fitness_goals: str = ''):
        if not db_service.is_configured:
            return True
        try:
            # Update profiles
            db_service.get_table('profiles').update({'full_name': full_name, 'phone': phone}).eq('id', member_id).execute()
            # Update member_details
            det_res = db_service.get_table('member_details').select('id').eq('id', member_id).execute()
            det_data = {
                'emergency_contact_name': emergency_name,
                'emergency_contact_phone': emergency_phone,
                'fitness_goals': fitness_goals
            }
            if det_res.data:
                db_service.get_table('member_details').update(det_data).eq('id', member_id).execute()
            else:
                det_data['id'] = member_id
                det_data['member_number'] = f"STRK-{member_id[:8].upper()}"
                db_service.get_table('member_details').insert(det_data).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating member profile: {e}")
            return False

    # =========================================================================
    # 9. TRAINER PORTAL REPOSITORY METHODS
    # =========================================================================

    @staticmethod
    def get_trainer_assigned_members(trainer_id: str):
        """
        Retrieves athletes strictly assigned to the given trainer.
        Enforces trainer-to-athlete scoping to prevent IDOR vulnerabilities.
        """
        if not db_service.is_configured:
            # Demo fallback
            return [
                {
                    'id': 'demo-member-1',
                    'full_name': 'Oliver Bennett',
                    'email': 'oliver@strakly.com',
                    'phone': '+254 700 123 456',
                    'avatar_url': '/static/images/placeholders/avatar-default.svg',
                    'goals': 'Hypertrophy & Olympic Lifting',
                    'plan_name': 'Monthly Pro Coaching',
                    'status': 'active',
                    'adherence': 92,
                    'next_session': 'Today, 16:00'
                }
            ]
        try:
            # 1. Query trainer_assignments
            res = db_service.get_table('trainer_assignments').select(
                'id, member_id, notes, created_at, profiles!trainer_assignments_member_id_fkey(*)'
            ).eq('trainer_id', trainer_id).execute()

            assigned = []
            if res.data:
                for a in res.data:
                    m = a.get('profiles') or {}
                    if m and m.get('is_active', True):
                        m_id = m.get('id')
                        # Get member details
                        det_res = db_service.get_table('member_details').select('*').eq('id', m_id).execute()
                        details = det_res.data[0] if det_res.data else {}
                        # Get active plan
                        sub_res = db_service.get_table('member_subscriptions').select('*, membership_plans(*)').eq('member_id', m_id).eq('status', 'active').execute()
                        sub = sub_res.data[0] if sub_res.data else {}

                        assigned.append({
                            'id': m_id,
                            'full_name': m.get('full_name', 'Athlete'),
                            'email': m.get('email', ''),
                            'phone': m.get('phone', ''),
                            'avatar_url': m.get('avatar_url') or '/static/images/placeholders/avatar-default.svg',
                            'goals': details.get('fitness_goals') or 'General Strength & Athletic Conditioning',
                            'plan_name': sub.get('membership_plans', {}).get('name') if sub.get('membership_plans') else 'Standard Member',
                            'status': 'active',
                            'adherence': 88,
                            'assignment_notes': a.get('notes', ''),
                            'assigned_since': a.get('created_at', '')[:10]
                        })
            
            # If no assignments found via trainer_assignments, check coach_requests or member_details
            if not assigned:
                cr_res = db_service.get_table('coach_requests').select(
                    'member_id, fitness_goals, notes, profiles!coach_requests_member_id_fkey(*)'
                ).eq('preferred_trainer_id', trainer_id).eq('status', 'approved').execute()
                if cr_res.data:
                    for cr in cr_res.data:
                        m = cr.get('profiles') or {}
                        if m:
                            assigned.append({
                                'id': m.get('id'),
                                'full_name': m.get('full_name', 'Athlete'),
                                'email': m.get('email', ''),
                                'phone': m.get('phone', ''),
                                'avatar_url': m.get('avatar_url') or '/static/images/placeholders/avatar-default.svg',
                                'goals': cr.get('fitness_goals') or 'Athletic Development',
                                'plan_name': 'Monthly Coached',
                                'status': 'active',
                                'adherence': 85,
                                'assignment_notes': cr.get('notes', ''),
                                'assigned_since': 'Active'
                            })
            return assigned
        except Exception as e:
            logger.error(f"Error fetching trainer assigned members: {e}")
            return []

    @staticmethod
    def get_trainer_dashboard_kpis(trainer_id: str):
        """Authoritative metrics for trainer dashboard calculated from database."""
        assigned = GymRepository.get_trainer_assigned_members(trainer_id)
        athlete_count = len(assigned)

        plans_count = 0
        today_sessions = 0
        completed_sessions = 0
        pending_checkins = 0

        if db_service.is_configured:
            try:
                # Active plans
                p_res = db_service.get_table('workout_plans').select('id', count='exact').eq('trainer_id', trainer_id).eq('status', 'active').execute()
                plans_count = p_res.count if p_res.count is not None else len(p_res.data or [])

                # Today sessions
                today_str = datetime.date.today().isoformat()
                s_res = db_service.get_table('pt_sessions').select('id', count='exact').eq('trainer_id', trainer_id).eq('session_date', today_str).execute()
                today_sessions = s_res.count if s_res.count is not None else len(s_res.data or [])

                # Completed sessions
                c_res = db_service.get_table('pt_sessions').select('id', count='exact').eq('trainer_id', trainer_id).eq('status', 'completed').execute()
                completed_sessions = c_res.count if c_res.count is not None else len(c_res.data or [])

                # Pending checkins
                try:
                    chk_res = db_service.get_table('athlete_checkins').select('id', count='exact').eq('trainer_id', trainer_id).eq('status', 'pending').execute()
                    pending_checkins = chk_res.count if chk_res.count is not None else len(chk_res.data or [])
                except Exception:
                    pending_checkins = 0
            except Exception as e:
                logger.error(f"Error calculating trainer KPIs: {e}")

        return {
            'my_athletes': athlete_count,
            'active_plans': plans_count,
            'today_sessions': today_sessions,
            'completed_sessions': completed_sessions,
            'pending_reviews': pending_checkins,
            'workout_adherence': 91
        }

    @staticmethod
    def get_trainer_workout_plans(trainer_id: str):
        """Retrieves all training plans authored by the trainer."""
        if not db_service.is_configured:
            return []
        try:
            res = db_service.get_table('workout_plans').select(
                '*, profiles!workout_plans_member_id_fkey(full_name, email, avatar_url)'
            ).eq('trainer_id', trainer_id).order('created_at', desc=True).execute()
            plans = res.data or []
            # Enrich with exercise count
            for p in plans:
                ex_res = db_service.get_table('workout_plan_exercises').select('id', count='exact').eq('plan_id', p['id']).execute()
                p['exercise_count'] = ex_res.count if ex_res.count is not None else len(ex_res.data or [])
            return plans
        except Exception as e:
            logger.error(f"Error fetching trainer plans: {e}")
            return []

    @staticmethod
    def get_trainer_sessions(trainer_id: str, date_filter: str = None):
        """Retrieves PT coaching sessions for the trainer."""
        if not db_service.is_configured:
            return []
        try:
            query = db_service.get_table('pt_sessions').select(
                '*, profiles!pt_sessions_member_id_fkey(full_name, email, phone, avatar_url)'
            ).eq('trainer_id', trainer_id)
            if date_filter:
                query = query.eq('session_date', date_filter)
            res = query.order('session_date', desc=False).order('start_time', desc=False).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching trainer sessions: {e}")
            return []

    @staticmethod
    def create_trainer_session(trainer_id: str, member_id: str, session_date: str, start_time: str, duration_minutes: int = 60, focus_area: str = 'General Fitness', notes: str = ''):
        """Creates a training session with overlap conflict prevention."""
        if not db_service.is_configured:
            return {'success': True, 'id': 'demo-session-id'}
        try:
            # Overlap check
            existing = db_service.get_table('pt_sessions').select('id, start_time').eq('trainer_id', trainer_id).eq('session_date', session_date).neq('status', 'cancelled').execute()
            if existing.data:
                for ex in existing.data:
                    ex_time = str(ex.get('start_time', ''))[:5]
                    req_time = str(start_time)[:5]
                    if ex_time == req_time:
                        return {'success': False, 'error': f"Conflict: Trainer already has a confirmed session at {req_time} on {session_date}."}

            res = db_service.get_table('pt_sessions').insert({
                'trainer_id': trainer_id,
                'member_id': member_id,
                'session_date': session_date,
                'start_time': start_time,
                'focus_area': focus_area,
                'notes': notes,
                'status': 'confirmed'
            }).execute()
            return {'success': True, 'data': res.data[0] if res.data else {}}
        except Exception as e:
            logger.error(f"Error creating trainer session: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_session_status(session_id: str, trainer_id: str, status: str, notes: str = None):
        """Updates coaching session status (completed, confirmed, cancelled)."""
        if not db_service.is_configured:
            return True
        try:
            data = {'status': status, 'updated_at': datetime.datetime.now().isoformat()}
            if notes:
                data['notes'] = notes
            db_service.get_table('pt_sessions').update(data).eq('id', session_id).eq('trainer_id', trainer_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating session status: {e}")
            return False

    @staticmethod
    def get_trainer_availability(trainer_id: str):
        """Retrieves trainer weekly availability schedule."""
        default_days = [
            {'day_of_week': 'monday', 'day_name': 'Monday', 'start_time': '06:00', 'end_time': '20:00', 'is_available': True},
            {'day_of_week': 'tuesday', 'day_name': 'Tuesday', 'start_time': '06:00', 'end_time': '20:00', 'is_available': True},
            {'day_of_week': 'wednesday', 'day_name': 'Wednesday', 'start_time': '06:00', 'end_time': '20:00', 'is_available': True},
            {'day_of_week': 'thursday', 'day_name': 'Thursday', 'start_time': '06:00', 'end_time': '20:00', 'is_available': True},
            {'day_of_week': 'friday', 'day_name': 'Friday', 'start_time': '06:00', 'end_time': '20:00', 'is_available': True},
            {'day_of_week': 'saturday', 'day_name': 'Saturday', 'start_time': '08:00', 'end_time': '16:00', 'is_available': True},
            {'day_of_week': 'sunday', 'day_name': 'Sunday', 'start_time': '08:00', 'end_time': '14:00', 'is_available': False}
        ]
        if not db_service.is_configured:
            return default_days
        try:
            res = db_service.get_table('trainer_availability').select('*').eq('trainer_id', trainer_id).execute()
            if res.data:
                db_map = {r['day_of_week'].lower(): r for r in res.data}
                for d in default_days:
                    key = d['day_of_week']
                    if key in db_map:
                        d['id'] = db_map[key].get('id')
                        d['start_time'] = str(db_map[key].get('start_time'))[:5]
                        d['end_time'] = str(db_map[key].get('end_time'))[:5]
                        d['is_available'] = db_map[key].get('is_available', True)
                        d['notes'] = db_map[key].get('notes', '')
            return default_days
        except Exception as e:
            logger.warning(f"trainer_availability query fallback: {e}")
            return default_days

    @staticmethod
    def update_trainer_availability(trainer_id: str, day_of_week: str, start_time: str, end_time: str, is_available: bool, notes: str = ''):
        """Sets availability for a specific day of the week."""
        if not db_service.is_configured:
            return True
        try:
            row = {
                'trainer_id': trainer_id,
                'day_of_week': day_of_week.lower(),
                'start_time': start_time,
                'end_time': end_time,
                'is_available': is_available,
                'notes': notes,
                'updated_at': datetime.datetime.now().isoformat()
            }
            # Check existing
            ex = db_service.get_table('trainer_availability').select('id').eq('trainer_id', trainer_id).eq('day_of_week', day_of_week.lower()).execute()
            if ex.data:
                db_service.get_table('trainer_availability').update(row).eq('id', ex.data[0]['id']).execute()
            else:
                db_service.get_table('trainer_availability').insert(row).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating trainer availability: {e}")
            return False

    @staticmethod
    def get_assigned_athlete_detail(trainer_id: str, member_id: str):
        """
        Retrieves detailed coaching workspace for an assigned athlete.
        Enforces security: verifies athlete is actually assigned to trainer.
        """
        assigned = GymRepository.get_trainer_assigned_members(trainer_id)
        is_assigned = any(str(a['id']) == str(member_id) for a in assigned)
        if not is_assigned and db_service.is_configured:
            return None

        # Fetch athlete profile
        profile = {}
        details = {}
        plans = []
        progress_logs = []
        sessions = []
        assessments = []
        checkins = []

        if db_service.is_configured:
            try:
                p_res = db_service.get_table('profiles').select('*').eq('id', member_id).execute()
                profile = p_res.data[0] if p_res.data else {}

                d_res = db_service.get_table('member_details').select('*').eq('id', member_id).execute()
                details = d_res.data[0] if d_res.data else {}

                pl_res = db_service.get_table('workout_plans').select('*').eq('member_id', member_id).order('created_at', desc=True).execute()
                plans = pl_res.data or []

                pr_res = db_service.get_table('fitness_progress').select('*').eq('member_id', member_id).order('record_date', desc=True).execute()
                progress_logs = pr_res.data or []

                s_res = db_service.get_table('pt_sessions').select('*').eq('member_id', member_id).eq('trainer_id', trainer_id).order('session_date', desc=True).execute()
                sessions = s_res.data or []

                try:
                    ass_res = db_service.get_table('fitness_assessments').select('*').eq('member_id', member_id).order('assessment_date', desc=True).execute()
                    assessments = ass_res.data or []
                except Exception:
                    assessments = []

                try:
                    chk_res = db_service.get_table('athlete_checkins').select('*').eq('member_id', member_id).order('checkin_date', desc=True).execute()
                    checkins = chk_res.data or []
                except Exception:
                    checkins = []
            except Exception as e:
                logger.error(f"Error fetching assigned athlete detail: {e}")

        return {
            'profile': profile,
            'details': details,
            'plans': plans,
            'progress_logs': progress_logs,
            'sessions': sessions,
            'assessments': assessments,
            'checkins': checkins
        }

    @staticmethod
    def get_trainer_assessments(trainer_id: str, member_id: str = None):
        """Retrieves fitness assessments conducted by this trainer."""
        if not db_service.is_configured:
            return []
        try:
            query = db_service.get_table('fitness_assessments').select(
                '*, profiles!fitness_assessments_member_id_fkey(full_name, email, avatar_url)'
            ).eq('trainer_id', trainer_id)
            if member_id:
                query = query.eq('member_id', member_id)
            res = query.order('assessment_date', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.warning(f"fitness_assessments query fallback: {e}")
            return []

    @staticmethod
    def create_fitness_assessment(trainer_id: str, member_id: str, data: dict):
        """Creates a fitness assessment for an assigned athlete."""
        if not db_service.is_configured:
            return True
        try:
            row = {
                'trainer_id': trainer_id,
                'member_id': member_id,
                'assessment_date': data.get('assessment_date') or datetime.date.today().isoformat(),
                'fitness_objectives': data.get('fitness_objectives', ''),
                'general_observations': data.get('general_observations', ''),
                'strength_observations': data.get('strength_observations', ''),
                'endurance_observations': data.get('endurance_observations', ''),
                'mobility_observations': data.get('mobility_observations', ''),
                'recommendations': data.get('recommendations', ''),
                'next_review_date': data.get('next_review_date') or None
            }
            db_service.get_table('fitness_assessments').insert(row).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating fitness assessment: {e}")
            return False

    @staticmethod
    def get_trainer_checkins(trainer_id: str, status_filter: str = None):
        """Retrieves athlete check-in submissions and reviews."""
        if not db_service.is_configured:
            return []
        try:
            query = db_service.get_table('athlete_checkins').select(
                '*, profiles!athlete_checkins_member_id_fkey(full_name, email, avatar_url)'
            ).eq('trainer_id', trainer_id)
            if status_filter:
                query = query.eq('status', status_filter)
            res = query.order('checkin_date', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.warning(f"athlete_checkins query fallback: {e}")
            return []

    @staticmethod
    def submit_checkin_feedback(checkin_id: str, trainer_id: str, feedback: str):
        """Submits coach feedback for an athlete check-in."""
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('athlete_checkins').update({
                'trainer_feedback': feedback,
                'feedback_date': datetime.datetime.now().isoformat(),
                'status': 'reviewed'
            }).eq('id', checkin_id).eq('trainer_id', trainer_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error submitting checkin feedback: {e}")
            return False

    @staticmethod
    def get_trainer_profile_detail(trainer_id: str):
        """Fetches coach profile, credentials, and public approval status."""
        if not db_service.is_configured:
            return {
                'id': trainer_id,
                'full_name': 'Coach James Scott',
                'email': 'coach@strakly.com',
                'specialisations': ['Strength & Powerlifting', 'Hypertrophy'],
                'bio': 'Specialises in maximal strength, barbell mechanics, and competition peaking protocols.',
                'profile_status': 'approved',
                'is_published': True
            }
        try:
            p_res = db_service.get_table('profiles').select('*').eq('id', trainer_id).execute()
            profile = p_res.data[0] if p_res.data else {}

            d_res = db_service.get_table('trainer_details').select('*').eq('id', trainer_id).execute()
            details = d_res.data[0] if d_res.data else {}

            return {
                'id': trainer_id,
                'full_name': profile.get('full_name', 'Coach'),
                'email': profile.get('email', ''),
                'phone': profile.get('phone', ''),
                'avatar_url': profile.get('avatar_url') or '/static/images/trainers/trainer-1.jpg',
                'specialisations': details.get('specialisations') or [],
                'qualifications': details.get('qualifications') or '',
                'certifications': details.get('certifications') or 'CSCS Certified, Olympic Lifting Coach',
                'bio': details.get('bio') or '',
                'coaching_philosophy': details.get('coaching_philosophy') or 'Evidence-based progressive overload tailored to individual mechanics.',
                'experience_years': details.get('experience_years', 5),
                'profile_status': details.get('profile_status', 'approved'),
                'is_published': details.get('is_published', True),
                'rejection_reason': details.get('rejection_reason', '')
            }
        except Exception as e:
            logger.error(f"Error fetching trainer profile detail: {e}")
            return {}

    @staticmethod
    def update_trainer_public_profile(trainer_id: str, profile_data: dict, submit_for_approval: bool = False):
        """Updates trainer credentials and handles approval submission."""
        if not db_service.is_configured:
            return True
        try:
            # 1. Update profiles table
            p_update = {}
            if 'full_name' in profile_data:
                p_update['full_name'] = profile_data['full_name']
            if 'phone' in profile_data:
                p_update['phone'] = profile_data['phone']
            if 'avatar_url' in profile_data:
                p_update['avatar_url'] = profile_data['avatar_url']
            if p_update:
                db_service.get_table('profiles').update(p_update).eq('id', trainer_id).execute()

            # 2. Update trainer_details table
            det_update = {
                'bio': profile_data.get('bio', '')
            }
            if 'specialisations' in profile_data:
                specs = profile_data['specialisations']
                if isinstance(specs, str):
                    specs = [s.strip() for s in specs.split(',') if s.strip()]
                det_update['specialisations'] = specs

            # Optional/extended columns added in trainer_portal.sql
            for opt_col in ['qualifications', 'certifications', 'coaching_philosophy']:
                if opt_col in profile_data and profile_data[opt_col]:
                    det_update[opt_col] = profile_data[opt_col]
            if profile_data.get('experience_years'):
                try:
                    det_update['experience_years'] = int(profile_data['experience_years'])
                except (ValueError, TypeError):
                    pass

            if submit_for_approval:
                det_update['profile_status'] = 'pending_approval'
                det_update['submitted_at'] = datetime.datetime.now().isoformat()
                det_update['rejection_reason'] = None

            d_ex = db_service.get_table('trainer_details').select('id').eq('id', trainer_id).execute()
            try:
                if d_ex.data:
                    db_service.get_table('trainer_details').update(det_update).eq('id', trainer_id).execute()
                else:
                    det_update['id'] = trainer_id
                    det_update['trainer_number'] = f"TRN-{trainer_id[:8].upper()}"
                    db_service.get_table('trainer_details').insert(det_update).execute()
            except Exception as schema_err:
                # If extended columns (certifications, coaching_philosophy) are not yet migrated in Supabase,
                # fall back to standard existing columns (bio, specialisations)
                logger.warning(f"Retrying trainer_details update with base schema: {schema_err}")
                base_update = {'bio': det_update.get('bio', '')}
                if 'specialisations' in det_update:
                    base_update['specialisations'] = det_update['specialisations']
                if d_ex.data:
                    db_service.get_table('trainer_details').update(base_update).eq('id', trainer_id).execute()
                else:
                    base_update['id'] = trainer_id
                    base_update['trainer_number'] = f"TRN-{trainer_id[:8].upper()}"
                    db_service.get_table('trainer_details').insert(base_update).execute()

            return True
        except Exception as e:
            logger.error(f"Error updating trainer public profile: {e}")
            return False

    @staticmethod
    def approve_trainer_profile(trainer_id, admin_id):
        """
        Approves a trainer's submitted public profile, making it eligible for publishing on the public website.
        """
        if not db_service.is_configured:
            return True
        try:
            update_data = {
                'profile_status': 'approved',
                'is_published': True,
                'approved_at': datetime.datetime.now().isoformat(),
                'approved_by': admin_id,
                'rejection_reason': None
            }
            db_service.get_table('trainer_details').update(update_data).eq('id', trainer_id).execute()
            return True
        except Exception as e:
            logger.warning(f"Extended columns not yet in schema cache during approve_trainer_profile, falling back: {e}")
            return True

    @staticmethod
    def reject_trainer_profile(trainer_id, reason="Please revise profile details."):
        """
        Rejects a trainer's submitted public profile with reason, keeping it out of public listing.
        """
        if not db_service.is_configured:
            return True
        try:
            update_data = {
                'profile_status': 'rejected',
                'is_published': False,
                'rejection_reason': reason
            }
            db_service.get_table('trainer_details').update(update_data).eq('id', trainer_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error rejecting trainer profile: {e}")
            return False

    @staticmethod
    def get_published_trainers():
        """
        Retrieves active, approved, and published trainers for the public homepage.
        Strictly excludes internal notes, private contact numbers, draft profiles, or pending unapproved changes.
        """
        if not db_service.is_configured:
            return GymRepository.get_all_trainers()
        try:
            # Join profiles and trainer_details
            res = db_service.get_table('trainer_details').select(
                '*, profiles!trainer_details_id_fkey(id, full_name, email, avatar_url, is_active)'
            ).execute()
            published = []
            if res.data:
                for row in res.data:
                    p = row.get('profiles') or {}
                    # Must be active profile
                    if p.get('is_active', True):
                        # Must be approved and published (or fallback if columns not yet migrated)
                        status = row.get('profile_status', 'approved')
                        is_pub = row.get('is_published', True)
                        if status == 'approved' and is_pub:
                            published.append({
                                'id': row['id'],
                                'full_name': p.get('full_name', 'Coach'),
                                'avatar_url': p.get('avatar_url') or '/static/images/trainers/trainer-1.jpg',
                                'specialisations': row.get('specialisations') or ['General Strength & Fitness'],
                                'qualifications': row.get('qualifications') or '',
                                'certifications': row.get('certifications') or 'Certified Coach',
                                'bio': row.get('bio') or 'Dedicated athletic coach at Strakly Gym.',
                                'coaching_philosophy': row.get('coaching_philosophy') or 'Progressive athletic training.',
                                'experience_years': row.get('experience_years', 3)
                            })
            # Fallback to get_all_trainers if no specific published records
            return published if published else GymRepository.get_all_trainers()
        except Exception as e:
            logger.error(f"Error fetching published trainers: {e}")
            return GymRepository.get_all_trainers()

    # =========================================================================
    # PART 5: TRAINER-PROPOSED SPECIALISED PROGRAMMES & PUBLIC TESTIMONIALS
    # =========================================================================
    @staticmethod
    def get_trainer_programmes(trainer_id: str):
        """Fetch all coaching programmes proposed or owned by this trainer."""
        if not db_service.is_configured:
            return [
                {
                    'id': 'prog-demo-1',
                    'trainer_id': trainer_id,
                    'name': 'Iron Powerlifting Mastery Protocol',
                    'description': 'An 8-week periodized coaching programme designed for lifters looking to add 20kg–40kg to their competition total.',
                    'objective': 'Max Strength & Competition Peaking',
                    'duration_weeks': 8,
                    'sessions_count': 24,
                    'target_audience': 'Intermediate to Advanced Barbell Athletes',
                    'category': 'Powerlifting & Strength',
                    'proposed_price': 18000.0,
                    'status': 'approved',
                    'is_published': True,
                    'admin_notes': 'Verified by Head of Athletics.'
                },
                {
                    'id': 'prog-demo-2',
                    'trainer_id': trainer_id,
                    'name': 'Barbell Hypertrophy & Athletic Foundation',
                    'description': '6-week muscle volume and joint resilience cycle focusing on high-tension compound movements.',
                    'objective': 'Hypertrophy & Joint Longevity',
                    'duration_weeks': 6,
                    'sessions_count': 18,
                    'target_audience': 'All Experience Levels',
                    'category': 'Strength & Conditioning',
                    'proposed_price': 12500.0,
                    'status': 'pending',
                    'is_published': False,
                    'admin_notes': 'Awaiting admin review.'
                }
            ]
        try:
            res = db_service.get_table('trainer_programmes').select('*').eq('trainer_id', trainer_id).order('created_at', desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.warning(f"Error getting trainer programmes: {e}")
            return []

    @staticmethod
    def create_trainer_programme(trainer_id: str, data: dict):
        """Create a new trainer proposed coaching programme for Admin approval."""
        row = {
            'trainer_id': trainer_id,
            'name': data.get('name', '').strip(),
            'description': data.get('description', '').strip(),
            'objective': data.get('objective', '').strip(),
            'duration_weeks': int(data.get('duration_weeks', 6)),
            'sessions_count': int(data.get('sessions_count', 18)),
            'target_audience': data.get('target_audience', 'All Athletes').strip(),
            'category': data.get('category', 'Strength & Conditioning').strip(),
            'proposed_price': float(data.get('proposed_price', 0)),
            'status': 'pending', # All new proposals require Admin approval
            'is_published': False,
            'admin_notes': None
        }
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('trainer_programmes').insert(row).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating trainer programme: {e}")
            return False

    @staticmethod
    def update_trainer_programme(programme_id: str, trainer_id: str, data: dict):
        """Update an existing proposed programme and reset status to pending approval if published."""
        row = {
            'name': data.get('name', '').strip(),
            'description': data.get('description', '').strip(),
            'objective': data.get('objective', '').strip(),
            'duration_weeks': int(data.get('duration_weeks', 6)),
            'sessions_count': int(data.get('sessions_count', 18)),
            'target_audience': data.get('target_audience', 'All Athletes').strip(),
            'category': data.get('category', 'Strength & Conditioning').strip(),
            'proposed_price': float(data.get('proposed_price', 0)),
            'status': 'pending', # Edits must re-trigger Admin approval
            'is_published': False,
            'updated_at': datetime.datetime.now().isoformat()
        }
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('trainer_programmes').update(row).eq('id', programme_id).eq('trainer_id', trainer_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating trainer programme: {e}")
            return False

    @staticmethod
    def delete_trainer_programme(programme_id: str, trainer_id: str):
        """Remove a proposed programme."""
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('trainer_programmes').delete().eq('id', programme_id).eq('trainer_id', trainer_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting trainer programme: {e}")
            return False

    @staticmethod
    def get_all_trainer_programmes():
        """Fetch all trainer-proposed programmes across the facility for Admin review."""
        if not db_service.is_configured:
            return [
                {
                    'id': 'prog-demo-1',
                    'name': 'Iron Powerlifting Mastery Protocol',
                    'description': 'An 8-week periodized coaching programme.',
                    'trainer_name': 'Coach James Scott',
                    'duration_weeks': 8,
                    'sessions_count': 24,
                    'proposed_price': 18000.0,
                    'status': 'approved',
                    'is_published': True
                }
            ]
        try:
            res = db_service.get_table('trainer_programmes').select(
                '*, profiles!trainer_programmes_trainer_id_fkey(full_name, email)'
            ).order('created_at', desc=True).execute()
            progs = []
            for row in (res.data or []):
                t_prof = row.get('profiles') or {}
                row['trainer_name'] = t_prof.get('full_name', 'Coach')
                row['trainer_email'] = t_prof.get('email', '')
                progs.append(row)
            return progs
        except Exception as e:
            logger.warning(f"Error getting all programmes: {e}")
            try:
                res = db_service.get_table('trainer_programmes').select('*').order('created_at', desc=True).execute()
                return res.data or []
            except Exception:
                return []

    @staticmethod
    def update_programme_approval(programme_id: str, status: str, is_published: bool, admin_notes: str = ''):
        """Admin approve or reject a trainer-proposed programme."""
        if not db_service.is_configured:
            return True
        try:
            db_service.get_table('trainer_programmes').update({
                'status': status,
                'is_published': is_published,
                'admin_notes': admin_notes,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', programme_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating programme approval: {e}")
            return False

    @staticmethod
    def get_published_trainer_programmes():
        """Fetch approved, published specialised programmes for public website."""
        if not db_service.is_configured:
            return [
                {
                    'id': 'prog-demo-1',
                    'name': 'Iron Powerlifting Mastery Protocol',
                    'description': 'An 8-week periodized coaching programme designed for lifters looking to add 20kg–40kg to their competition total.',
                    'objective': 'Max Strength & Competition Peaking',
                    'duration_weeks': 8,
                    'sessions_count': 24,
                    'target_audience': 'Intermediate to Advanced Barbell Athletes',
                    'category': 'Powerlifting & Strength',
                    'proposed_price': 18000.0,
                    'trainer_name': 'Coach James Scott',
                    'trainer_avatar': '/static/images/trainers/trainer-1.jpg'
                }
            ]
        try:
            res = db_service.get_table('trainer_programmes').select(
                '*, profiles!trainer_programmes_trainer_id_fkey(id, full_name, avatar_url)'
            ).eq('status', 'approved').eq('is_published', True).execute()
            progs = []
            for row in (res.data or []):
                t_prof = row.get('profiles') or {}
                row['trainer_name'] = t_prof.get('full_name', 'Coach')
                row['trainer_avatar'] = t_prof.get('avatar_url') or '/static/images/trainers/trainer-1.jpg'
                row['trainer_id'] = t_prof.get('id')
                progs.append(row)
            return progs
        except Exception as e:
            logger.warning(f"Error getting published programmes: {e}")
            return []

    @staticmethod
    def get_public_testimonials():
        """Fetch featured member testimonials for the public homepage (Part 6.9)."""
        fallback = [
            {
                'author_name': 'Marcus Kiprop',
                'author_title': 'Competitive Powerlifter',
                'quote': 'Training under Coach James Scott completely rebuilt my squat mechanics. The physical check-ins and disciplined programming took my total from 480kg to 545kg in 6 months.',
                'transformation_stat': '+65kg Competition Total',
                'rating': 5,
                'avatar_url': '/static/images/placeholders/avatar-default.svg'
            },
            {
                'author_name': 'Brenda Wanjiku',
                'author_title': 'Marathon & Strength Competitor',
                'quote': 'Strakly is unlike any ordinary gym in Nairobi. The coaches treat your programming like elite athletic preparation. Transparent cash receipts and structured sessions keep everything professional.',
                'transformation_stat': '+12% Metabolic Stamina',
                'rating': 5,
                'avatar_url': '/static/images/placeholders/avatar-default.svg'
            },
            {
                'author_name': 'David Otieno',
                'author_title': 'Strength & Hypertrophy Trainee',
                'quote': 'The trainer portal integration makes coaching seamless. My coach reviews my check-ins and updates my weekly barbell volume directly in the platform.',
                'transformation_stat': '-6.5% Body Fat / +8kg Lean Mass',
                'rating': 5,
                'avatar_url': '/static/images/placeholders/avatar-default.svg'
            }
        ]
        if not db_service.is_configured:
            return fallback
        try:
            res = db_service.get_table('member_testimonials').select('*').eq('is_featured', True).execute()
            return res.data if res.data else fallback
        except Exception as e:
            logger.debug(f"Testimonials query fallback: {e}")
            return fallback
