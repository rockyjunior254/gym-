import os
import uuid
import datetime
import io
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, jsonify
from app.services.auth_service import admin_required
from app.services.repository import GymRepository
from app.services.supabase_client import db_service
from app.services.audit_service import log_audit

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@admin_required
def check_admin_access():
    pass

# =============================================================================
# 1. ADMIN DASHBOARD (ANALYTICS CENTRE)
# =============================================================================
@admin_bp.route('/dashboard')
def dashboard():
    period = request.args.get('period', '30d')
    kpis = GymRepository.get_admin_dashboard_kpis()
    chart_analytics = GymRepository.get_admin_chart_analytics(period=period)
    
    # Recent activity items
    recent_members = GymRepository.get_all_members()[:5]
    recent_payments = GymRepository.get_all_cash_payments()[:5]
    recent_attendance = GymRepository.get_all_attendance()[:5]
    recent_audit = GymRepository.get_audit_logs(limit=8)
    upcoming_classes = GymRepository.get_upcoming_classes()[:5]
    
    subscriptions = GymRepository.get_all_subscriptions()
    pending_subscriptions = [s for s in subscriptions if s.get('status') == 'pending']

    return render_template('admin/dashboard.html',
                           kpis=kpis,
                           total_members=kpis.get('total_members', 0),
                           active_subscriptions=kpis.get('active_members', 0),
                           expired_subscriptions=kpis.get('expired_memberships', 0),
                           new_registrations=kpis.get('new_registrations', 0),
                           today_attendance=kpis.get('today_attendance', 0),
                           total_cash=kpis.get('total_cash_collected', 0.0),
                           upcoming_classes=kpis.get('upcoming_classes', 0),
                           active_trainers=kpis.get('active_trainers', 0),
                           chart_analytics=chart_analytics,
                           range_param=period,
                           period=period,
                           recent_members=recent_members,
                           recent_payments=recent_payments,
                           recent_attendance=recent_attendance,
                           recent_audit=recent_audit,
                           pending_subscriptions=pending_subscriptions)

# =============================================================================
# 2. MEMBER MANAGEMENT (FULL CRUD & 360 PROFILE)
# =============================================================================
@admin_bp.route('/members', methods=['GET', 'POST'])
def members():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        emergency_name = request.form.get('emergency_contact_name', '').strip()
        emergency_phone = request.form.get('emergency_contact_phone', '').strip()
        goals = request.form.get('fitness_goals', '').strip()
        plan_id = request.form.get('plan_id')

        if not full_name or not email:
            flash('Member name and email are mandatory.', 'warning')
            return redirect(url_for('admin.members'))

        if db_service.is_configured:
            try:
                # Check for existing profile by email
                existing = db_service.get_table('profiles').select('id').eq('email', email).execute()
                if existing.data:
                    flash(f"A member profile with email '{email}' already exists.", 'warning')
                    return redirect(url_for('admin.members'))

                user_id = str(uuid.uuid4())
                member_num = f"STK-M-{uuid.uuid4().hex[:5].upper()}"

                db_service.get_table('profiles').insert({
                    'id': user_id,
                    'email': email,
                    'full_name': full_name,
                    'phone': phone,
                    'role': 'member',
                    'is_active': True,
                    'is_archived': False
                }).execute()

                db_service.get_table('member_details').insert({
                    'id': user_id,
                    'member_number': member_num,
                    'emergency_contact_name': emergency_name,
                    'emergency_contact_phone': emergency_phone,
                    'fitness_goals': goals,
                    'joined_date': datetime.date.today().isoformat()
                }).execute()

                if plan_id:
                    db_service.get_table('member_subscriptions').insert({
                        'member_id': user_id,
                        'plan_id': plan_id,
                        'status': 'pending',
                        'notes': 'Admin registration awaiting cash confirmation'
                    }).execute()

                log_audit(session['user']['id'], 'admin', 'MEMBER_REGISTER', 'profiles', user_id, {'name': full_name, 'member_number': member_num})
                flash(f"Athlete {full_name} ({member_num}) registered successfully.", 'success')
            except Exception as e:
                flash(f"Error registering member: {str(e)}", 'danger')
        else:
            flash(f"Athlete {full_name} registered (Config mode).", 'info')
        return redirect(url_for('admin.members'))

    search_query = request.args.get('q', '').strip().lower()
    status_filter = request.args.get('status', 'all')
    all_members = GymRepository.get_all_members(include_archived=True)

    filtered_members = all_members
    if search_query:
        filtered_members = [
            m for m in filtered_members
            if search_query in (m.get('full_name') or '').lower() or
               search_query in (m.get('email') or '').lower() or
               search_query in (m.get('member_details', {}).get('member_number') if m.get('member_details') else '').lower()
        ]
    if status_filter == 'active':
        filtered_members = [m for m in filtered_members if m.get('is_active') and not m.get('is_archived')]
    elif status_filter == 'inactive':
        filtered_members = [m for m in filtered_members if not m.get('is_active') or m.get('is_archived')]

    plans = GymRepository.get_active_plans()
    return render_template('admin/members.html', members=filtered_members, plans=plans, search_query=search_query, status_filter=status_filter)

@admin_bp.route('/members/<member_id>', methods=['GET', 'POST'])
def member_detail(member_id):
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        emergency_name = request.form.get('emergency_contact_name', '').strip()
        emergency_phone = request.form.get('emergency_contact_phone', '').strip()
        goals = request.form.get('fitness_goals', '').strip()
        medical_notes = request.form.get('medical_notes', '').strip()
        is_active = request.form.get('is_active') == 'on'

        profile_data = {
            'full_name': full_name,
            'phone': phone,
            'is_active': is_active
        }
        details_data = {
            'emergency_contact_name': emergency_name,
            'emergency_contact_phone': emergency_phone,
            'fitness_goals': goals,
            'medical_notes': medical_notes
        }

        try:
            GymRepository.update_member_profile(member_id, profile_data, details_data)
            log_audit(session['user']['id'], 'admin', 'MEMBER_UPDATE', 'profiles', member_id, profile_data)
            flash('Member profile updated successfully.', 'success')
        except Exception as e:
            flash(f"Error updating member profile: {str(e)}", 'danger')
        return redirect(url_for('admin.member_detail', member_id=member_id))

    detail = GymRepository.get_member_full_detail(member_id)
    if not detail:
        flash('Member record not found.', 'warning')
        return redirect(url_for('admin.members'))

    trainers = GymRepository.get_all_trainers()
    plans = GymRepository.get_active_plans()
    return render_template('admin/member_detail.html', detail=detail, trainers=trainers, plans=plans)

@admin_bp.route('/members/archive/<member_id>', methods=['POST'])
def archive_member(member_id):
    reason = request.form.get('reason', 'Administrative archival')
    GymRepository.archive_member(member_id)
    log_audit(session['user']['id'], 'admin', 'MEMBER_ARCHIVE', 'profiles', member_id, reason=reason)
    flash('Member record archived safely. Historical financial and attendance records remain preserved.', 'info')
    return redirect(url_for('admin.members'))

@admin_bp.route('/members/delete/<member_id>', methods=['POST'])
def delete_member(member_id):
    try:
        GymRepository.delete_member(member_id)
        log_audit(session['user']['id'], 'admin', 'MEMBER_DELETE', 'profiles', member_id)
        flash('Athlete user account and related records deleted permanently.', 'info')
    except Exception as e:
        flash(f"Error deleting athlete account: {str(e)}", 'danger')
    return redirect(url_for('admin.members'))

@admin_bp.route('/members/edit/<member_id>', methods=['POST'])
def edit_member(member_id):
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    emergency_name = request.form.get('emergency_contact_name', '').strip()
    emergency_phone = request.form.get('emergency_contact_phone', '').strip()
    goals = request.form.get('fitness_goals', '').strip()
    is_active = request.form.get('is_active') == 'true' or request.form.get('is_active') == 'on'

    profile_data = {
        'full_name': full_name,
        'phone': phone,
        'is_active': is_active
    }
    details_data = {
        'emergency_contact_name': emergency_name,
        'emergency_contact_phone': emergency_phone,
        'fitness_goals': goals
    }
    try:
        GymRepository.update_member_profile(member_id, profile_data, details_data)
        log_audit(session['user']['id'], 'admin', 'MEMBER_UPDATE', 'profiles', member_id, profile_data)
        flash(f"Athlete profile '{full_name}' updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating athlete profile: {str(e)}", 'danger')
    return redirect(url_for('admin.members'))

# =============================================================================
# 3. MEMBERSHIP PLANS & PACKAGES
# =============================================================================
@admin_bp.route('/plans', methods=['GET', 'POST'])
def plans():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        duration_type = request.form.get('duration_type', 'monthly')
        duration_days = int(request.form.get('duration_days', 30))
        price = float(request.form.get('price', 0))
        description = request.form.get('description', '')
        benefits_raw = request.form.get('benefits', '')
        benefits = [b.strip() for b in benefits_raw.split('\n') if b.strip()]

        if db_service.is_configured:
            try:
                res = db_service.get_table('membership_plans').insert({
                    'name': name,
                    'duration_type': duration_type,
                    'duration_days': duration_days,
                    'price': price,
                    'description': description,
                    'benefits': benefits,
                    'is_active': True,
                    'is_archived': False
                }).execute()
                log_audit(session['user']['id'], 'admin', 'PLAN_CREATE', 'membership_plans', res.data[0]['id'] if res.data else None, {'name': name, 'price': price})
                flash(f"Plan '{name}' created successfully.", 'success')
            except Exception as e:
                flash(f"Error creating plan: {str(e)}", 'danger')
        else:
            flash(f"Plan '{name}' created (Config mode).", 'info')
        return redirect(url_for('admin.plans'))

    plans_list = GymRepository.get_all_plans(include_archived=True)
    return render_template('admin/plans.html', plans=plans_list)

@admin_bp.route('/plans/edit/<plan_id>', methods=['POST'])
def edit_plan(plan_id):
    name = request.form.get('name', '').strip()
    duration_type = request.form.get('duration_type', 'monthly')
    duration_days = int(request.form.get('duration_days', 30))
    price = float(request.form.get('price', 0))
    description = request.form.get('description', '').strip()
    benefits_raw = request.form.get('benefits', '')
    benefits = [b.strip() for b in benefits_raw.split('\n') if b.strip()]
    is_active = request.form.get('is_active') == 'true' or request.form.get('is_active') == 'on'

    plan_data = {
        'name': name,
        'duration_type': duration_type,
        'duration_days': duration_days,
        'price': price,
        'description': description,
        'benefits': benefits,
        'is_active': is_active
    }
    try:
        GymRepository.update_plan(plan_id, plan_data)
        log_audit(session['user']['id'], 'admin', 'PLAN_UPDATE', 'membership_plans', plan_id, plan_data)
        flash(f"Membership package '{name}' updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating plan: {str(e)}", 'danger')
    return redirect(url_for('admin.plans'))

@admin_bp.route('/plans/archive/<plan_id>', methods=['POST'])
def archive_plan(plan_id):
    GymRepository.archive_plan(plan_id)
    log_audit(session['user']['id'], 'admin', 'PLAN_ARCHIVE', 'membership_plans', plan_id)
    flash('Membership package archived. Historical subscriptions retain their original terms.', 'info')
    return redirect(url_for('admin.plans'))

# =============================================================================
# 4. SUBSCRIPTIONS & RENEWALS
# =============================================================================
@admin_bp.route('/subscriptions', methods=['GET', 'POST'])
def subscriptions():
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        plan_id = request.form.get('plan_id')
        notes = request.form.get('notes', '')

        if not member_id or not plan_id:
            flash('Please select both a member and a membership plan.', 'warning')
            return redirect(url_for('admin.subscriptions'))

        if db_service.is_configured:
            try:
                res = db_service.get_table('member_subscriptions').insert({
                    'member_id': member_id,
                    'plan_id': plan_id,
                    'status': 'pending',
                    'notes': notes
                }).execute()
                log_audit(session['user']['id'], 'admin', 'SUBSCRIPTION_CREATE', 'member_subscriptions', res.data[0]['id'] if res.data else None)
                flash('Subscription request created in PENDING status. Awaiting cash verification.', 'success')
            except Exception as e:
                flash(f"Error creating subscription: {str(e)}", 'danger')
        else:
            flash('Subscription request recorded (Config mode).', 'info')
        return redirect(url_for('admin.subscriptions'))

    subs = GymRepository.get_all_subscriptions()
    members = GymRepository.get_all_members()
    plans = GymRepository.get_active_plans()
    return render_template('admin/subscriptions.html', subscriptions=subs, members=members, plans=plans)

@admin_bp.route('/subscriptions/activate/<sub_id>', methods=['POST'])
def activate_subscription(sub_id):
    if db_service.is_configured:
        try:
            today = datetime.date.today()
            sub = db_service.get_table('member_subscriptions').select('*, membership_plans(duration_days)').eq('id', sub_id).execute()
            duration = 30
            if sub.data and sub.data[0].get('membership_plans'):
                duration = sub.data[0]['membership_plans'].get('duration_days', 30)
            end_date = today + datetime.timedelta(days=duration)

            db_service.get_table('member_subscriptions').update({
                'status': 'active',
                'start_date': today.isoformat(),
                'end_date': end_date.isoformat(),
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', sub_id).execute()

            log_audit(session['user']['id'], 'admin', 'SUBSCRIPTION_ACTIVATE', 'member_subscriptions', sub_id, {'start': today.isoformat(), 'end': end_date.isoformat()})
            flash(f"Subscription activated! Valid through {end_date.isoformat()}.", 'success')
        except Exception as e:
            flash(f"Error activating subscription: {str(e)}", 'danger')
    else:
        flash('Subscription marked active (Evaluation mode).', 'info')
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/subscriptions/cancel/<sub_id>', methods=['POST'])
def cancel_subscription(sub_id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Cancellation reason is required.', 'warning')
        return redirect(url_for('admin.subscriptions'))

    if db_service.is_configured:
        try:
            db_service.get_table('member_subscriptions').update({
                'status': 'cancelled',
                'cancelled_at': datetime.datetime.now().isoformat(),
                'cancellation_reason': reason,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', sub_id).execute()
            log_audit(session['user']['id'], 'admin', 'SUBSCRIPTION_CANCEL', 'member_subscriptions', sub_id, reason=reason)
            flash('Subscription cancelled.', 'warning')
        except Exception as e:
            flash(f"Error cancelling subscription: {str(e)}", 'danger')
    else:
        flash(f"Subscription cancelled with reason: '{reason}' (Config mode).", 'info')
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/subscriptions/renew/<sub_id>', methods=['POST'])
def renew_subscription(sub_id):
    days = int(request.form.get('extension_days', 30))
    try:
        GymRepository.renew_subscription(sub_id, extension_days=days)
        log_audit(session['user']['id'], 'admin', 'SUBSCRIPTION_RENEW', 'member_subscriptions', sub_id, {'extension_days': days})
        flash(f"Subscription renewed successfully (+{days} days).", 'success')
    except Exception as e:
        flash(f"Error renewing subscription: {str(e)}", 'danger')
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/subscriptions/delete/<sub_id>', methods=['POST'])
def delete_subscription(sub_id):
    try:
        GymRepository.delete_subscription(sub_id)
        log_audit(session['user']['id'], 'admin', 'SUBSCRIPTION_DELETE', 'member_subscriptions', sub_id)
        flash('Subscription record removed.', 'info')
    except Exception as e:
        flash(f"Error deleting subscription: {str(e)}", 'danger')
    return redirect(url_for('admin.subscriptions'))

# =============================================================================
# 5. CASH PAYMENTS & RECEIPTS (STRICT CASH ONLY)
# =============================================================================
@admin_bp.route('/payments', methods=['GET', 'POST'])
def payments():
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        subscription_id = request.form.get('subscription_id') or None
        amount = float(request.form.get('amount', 0))
        notes = request.form.get('notes', '')
        receipt_num = GymRepository.generate_receipt_number()

        if amount <= 0:
            flash('Payment amount must be greater than zero.', 'warning')
            return redirect(url_for('admin.payments'))

        if db_service.is_configured:
            try:
                res = db_service.get_table('cash_payments').insert({
                    'receipt_number': receipt_num,
                    'member_id': member_id,
                    'subscription_id': subscription_id,
                    'amount': amount,
                    'payment_method': 'CASH',
                    'recorded_by': session['user']['id'],
                    'status': 'confirmed',
                    'notes': notes
                }).execute()

                log_audit(session['user']['id'], 'admin', 'CASH_PAYMENT_RECORD', 'cash_payments', res.data[0]['id'] if res.data else receipt_num, {'amount': amount, 'receipt': receipt_num})
                flash(f"Cash payment of KES {amount:,.2f} recorded. Official Receipt #{receipt_num} generated.", 'success')
            except Exception as e:
                flash(f"Error recording cash payment: {str(e)}", 'danger')
        else:
            flash(f"Cash payment of KES {amount:,.2f} recorded with Receipt #{receipt_num} (Config mode).", 'success')
        return redirect(url_for('admin.payments'))

    payments_list = GymRepository.get_all_cash_payments()
    members_list = GymRepository.get_all_members()
    subscriptions_list = GymRepository.get_all_subscriptions()
    return render_template('admin/payments.html', payments=payments_list, members=members_list, subscriptions=subscriptions_list)

@admin_bp.route('/payments/reversal/<payment_id>', methods=['POST'])
def reverse_payment(payment_id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('A clear reversal reason is mandatory for financial corrections.', 'warning')
        return redirect(url_for('admin.payments'))

    if db_service.is_configured:
        try:
            db_service.get_table('cash_payments').update({
                'status': 'reversed',
                'correction_reason': reason,
                'reversed_at': datetime.datetime.now().isoformat(),
                'reversed_by': session['user']['id'],
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', payment_id).execute()

            log_audit(session['user']['id'], 'admin', 'PAYMENT_REVERSAL', 'cash_payments', payment_id, reason=reason)
            flash(f"Payment marked reversed. Reason: {reason}", 'warning')
        except Exception as e:
            flash(f"Error reversing payment: {str(e)}", 'danger')
    else:
        log_audit(session['user']['id'], 'admin', 'PAYMENT_REVERSAL', 'cash_payments', payment_id, reason=reason)
        flash(f"Payment reversal recorded with reason: '{reason}' (Config mode).", 'info')
    return redirect(url_for('admin.payments'))

# =============================================================================
# 6. MANUAL ATTENDANCE (STRICTLY NO SCANNING)
# =============================================================================
@admin_bp.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        notes = request.form.get('notes', '')

        if not member_id:
            flash('Please select a member for check-in.', 'warning')
            return redirect(url_for('admin.attendance'))

        if db_service.is_configured:
            try:
                # Check eligibility
                subs = db_service.get_table('member_subscriptions').select('*').eq('member_id', member_id).eq('status', 'active').execute()
                status = 'present' if subs.data else 'exception'
                if status == 'exception':
                    notes = f"[EXCEPTION: Inactive Subscription] {notes}".strip()

                db_service.get_table('manual_attendance').insert({
                    'member_id': member_id,
                    'recorded_by': session['user']['id'],
                    'status': status,
                    'notes': notes
                }).execute()

                log_audit(session['user']['id'], 'admin', 'MANUAL_ATTENDANCE_CHECKIN', 'manual_attendance', member_id, {'status': status, 'notes': notes})
                flash(f"Attendance recorded successfully ({status.upper()}).", 'success')
            except Exception as e:
                flash(f"Error checking in member: {str(e)}", 'danger')
        else:
            flash("Attendance check-in saved manually (Config mode).", 'success')
        return redirect(url_for('admin.attendance'))

    date_filter = request.args.get('date', datetime.date.today().isoformat())
    attendance_list = GymRepository.get_all_attendance(date_filter=date_filter)
    members_list = GymRepository.get_all_members()
    return render_template('admin/attendance.html', attendance=attendance_list, members=members_list, selected_date=date_filter)

@admin_bp.route('/attendance/delete/<attendance_id>', methods=['POST'])
def delete_attendance(attendance_id):
    try:
        GymRepository.delete_attendance(attendance_id)
        log_audit(session['user']['id'], 'admin', 'ATTENDANCE_VOID', 'manual_attendance', attendance_id)
        flash('Check-in record removed successfully.', 'info')
    except Exception as e:
        flash(f"Error removing attendance record: {str(e)}", 'danger')
    return redirect(url_for('admin.attendance'))

# =============================================================================
# 7. TRAINER MANAGEMENT & ASSIGNMENTS
# =============================================================================
@admin_bp.route('/trainers', methods=['GET', 'POST'])
def trainers():
    if request.method == 'POST':
        action = request.form.get('action', 'assign')

        if action == 'create':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            specs_raw = request.form.get('specialisations', '')
            specialisations = [s.strip() for s in specs_raw.split(',') if s.strip()]
            bio = request.form.get('bio', '').strip()

            try:
                GymRepository.create_trainer_account(full_name, email, phone, specialisations, bio)
                log_audit(session['user']['id'], 'admin', 'TRAINER_CREATE', 'profiles', None, {'name': full_name, 'email': email})
                flash(f"Coach '{full_name}' created and linked successfully.", 'success')
            except Exception as e:
                flash(f"Error creating coach: {str(e)}", 'danger')
            return redirect(url_for('admin.trainers'))

        # Assignment workflow
        member_id = request.form.get('member_id')
        trainer_id = request.form.get('trainer_id')
        notes = request.form.get('notes', '')

        if db_service.is_configured:
            try:
                db_service.get_table('trainer_assignments').insert({
                    'member_id': member_id,
                    'trainer_id': trainer_id,
                    'assigned_by': session['user']['id'],
                    'notes': notes,
                    'status': 'active'
                }).execute()

                log_audit(session['user']['id'], 'admin', 'TRAINER_ASSIGNMENT', 'trainer_assignments', member_id, {'trainer_id': trainer_id})
                flash('Trainer assigned to athlete successfully.', 'success')
            except Exception as e:
                flash(f"Error assigning trainer: {str(e)}", 'danger')
        else:
            flash('Trainer assigned to athlete (Config mode).', 'info')
        return redirect(url_for('admin.trainers'))

    trainers_list = GymRepository.get_all_trainers()
    members_list = GymRepository.get_all_members()
    assignments_list = GymRepository.get_all_trainer_assignments()
    return render_template('admin/trainers.html', trainers=trainers_list, members=members_list, assignments=assignments_list)

@admin_bp.route('/trainers/edit/<trainer_id>', methods=['POST'])
def edit_trainer(trainer_id):
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    specs_raw = request.form.get('specialisations', '')
    specialisations = [s.strip() for s in specs_raw.split(',') if s.strip()]
    bio = request.form.get('bio', '').strip()

    try:
        GymRepository.edit_trainer(trainer_id, full_name, phone, specialisations, bio)
        log_audit(session['user']['id'], 'admin', 'TRAINER_EDIT', 'profiles', trainer_id, {'name': full_name})
        flash(f"Coach '{full_name}' updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating coach: {str(e)}", 'danger')
    return redirect(url_for('admin.trainers'))

@admin_bp.route('/trainers/toggle-active/<trainer_id>', methods=['POST'])
def toggle_trainer_active(trainer_id):
    try:
        current_profile = db_service.get_table('profiles').select('is_active').eq('id', trainer_id).execute()
        current_state = current_profile.data[0].get('is_active', True) if current_profile.data else True
        new_state = not current_state
        GymRepository.toggle_user_active(trainer_id, is_active=new_state)
        action_name = 'TRAINER_ACTIVATE' if new_state else 'TRAINER_SUSPEND'
        log_audit(session['user']['id'], 'admin', action_name, 'profiles', trainer_id)
        msg = 're-activated' if new_state else 'suspended'
        flash(f"Coach account successfully {msg}.", 'info')
    except Exception as e:
        flash(f"Error modifying coach status: {str(e)}", 'danger')
    return redirect(url_for('admin.trainers'))

@admin_bp.route('/trainers/archive/<trainer_id>', methods=['POST'])
def archive_trainer(trainer_id):
    try:
        GymRepository.archive_trainer(trainer_id)
        log_audit(session['user']['id'], 'admin', 'TRAINER_ARCHIVE', 'profiles', trainer_id)
        flash('Coach record archived safely. Assigned athletes have been freed for reassignment.', 'info')
    except Exception as e:
        flash(f"Error archiving coach: {str(e)}", 'danger')
    return redirect(url_for('admin.trainers'))

@admin_bp.route('/trainers/approve/<trainer_id>', methods=['POST'])
def approve_trainer_profile(trainer_id):
    try:
        success = GymRepository.approve_trainer_profile(trainer_id, session['user']['id'])
        if success:
            log_audit(session['user']['id'], 'admin', 'TRAINER_PROFILE_APPROVE', 'trainer_details', trainer_id)
            flash('Coach public profile approved and published to website.', 'success')
        else:
            flash('Failed to approve coach profile.', 'danger')
    except Exception as e:
        flash(f"Error approving coach profile: {str(e)}", 'danger')
    return redirect(url_for('admin.trainers'))

@admin_bp.route('/trainers/reject/<trainer_id>', methods=['POST'])
def reject_trainer_profile(trainer_id):
    reason = request.form.get('rejection_reason', 'Profile details require adjustment before publication.')
    try:
        success = GymRepository.reject_trainer_profile(trainer_id, reason=reason)
        if success:
            log_audit(session['user']['id'], 'admin', 'TRAINER_PROFILE_REJECT', 'trainer_details', trainer_id, {'reason': reason})
            flash('Coach public profile rejected and returned for revision.', 'info')
        else:
            flash('Failed to reject coach profile.', 'danger')
    except Exception as e:
        flash(f"Error rejecting coach profile: {str(e)}", 'danger')
    return redirect(url_for('admin.trainers'))

# =============================================================================
# 8. CLASSES & BOOKINGS
# =============================================================================
@admin_bp.route('/classes', methods=['GET', 'POST'])
def classes():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        class_date = request.form.get('class_date')
        start_time = request.form.get('start_time')
        duration = int(request.form.get('duration_minutes', 60))
        capacity = int(request.form.get('capacity', 20))
        description = request.form.get('description', '')
        trainer_id = request.form.get('trainer_id') or None

        if db_service.is_configured:
            try:
                db_service.get_table('fitness_classes').insert({
                    'name': name,
                    'class_date': class_date,
                    'start_time': start_time,
                    'duration_minutes': duration,
                    'capacity': capacity,
                    'description': description,
                    'trainer_id': trainer_id,
                    'image_url': '/static/images/classes/iron-strength.jpg',
                    'is_published': True
                }).execute()

                log_audit(session['user']['id'], 'admin', 'CLASS_CREATE', 'fitness_classes', None, {'name': name, 'date': class_date})
                flash(f"Class '{name}' scheduled for {class_date}.", 'success')
            except Exception as e:
                flash(f"Error scheduling class: {str(e)}", 'danger')
        else:
            flash(f"Class '{name}' scheduled (Config mode).", 'info')
        return redirect(url_for('admin.classes'))

    classes_list = GymRepository.get_all_classes()
    trainers_list = GymRepository.get_all_trainers()
    return render_template('admin/classes.html', classes=classes_list, trainers=trainers_list)

@admin_bp.route('/classes/cancel/<class_id>', methods=['POST'])
def cancel_class(class_id):
    if db_service.is_configured:
        try:
            db_service.get_table('fitness_classes').update({'is_cancelled': True}).eq('id', class_id).execute()
            log_audit(session['user']['id'], 'admin', 'CLASS_CANCEL', 'fitness_classes', class_id)
            flash('Class cancelled successfully.', 'info')
        except Exception as e:
            flash(f"Error cancelling class: {str(e)}", 'danger')
    return redirect(url_for('admin.classes'))

@admin_bp.route('/classes/delete/<class_id>', methods=['POST'])
def delete_class(class_id):
    if db_service.is_configured:
        try:
            db_service.get_table('fitness_classes').delete().eq('id', class_id).execute()
            log_audit(session['user']['id'], 'admin', 'CLASS_DELETE', 'fitness_classes', class_id)
            flash('Class removed successfully.', 'info')
        except Exception as e:
            flash(f"Error deleting class: {str(e)}", 'danger')
    return redirect(url_for('admin.classes'))

@admin_bp.route('/classes/edit/<class_id>', methods=['POST'])
def edit_class(class_id):
    name = request.form.get('name', '').strip()
    class_date = request.form.get('class_date')
    start_time = request.form.get('start_time')
    duration = int(request.form.get('duration_minutes', 60))
    capacity = int(request.form.get('capacity', 20))
    description = request.form.get('description', '')
    trainer_id = request.form.get('trainer_id') or None

    try:
        db_service.get_table('fitness_classes').update({
            'name': name,
            'class_date': class_date,
            'start_time': start_time,
            'duration_minutes': duration,
            'capacity': capacity,
            'description': description,
            'trainer_id': trainer_id,
            'updated_at': datetime.datetime.now().isoformat()
        }).eq('id', class_id).execute()
        log_audit(session['user']['id'], 'admin', 'CLASS_UPDATE', 'fitness_classes', class_id, {'name': name})
        flash(f"Class session '{name}' updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating class: {str(e)}", 'danger')
    return redirect(url_for('admin.classes'))

# =============================================================================
# 9. WORKOUT & EXERCISE MANAGEMENT
# =============================================================================
@admin_bp.route('/exercises', methods=['GET', 'POST'])
def exercises():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Strength')
        target_muscle = request.form.get('target_muscle_group', '')
        difficulty = request.form.get('difficulty', 'Beginner')
        instructions = request.form.get('instructions', '')
        equipment_req = request.form.get('equipment_required', '')

        if db_service.is_configured:
            try:
                db_service.get_table('exercise_library').insert({
                    'name': name,
                    'category': category,
                    'target_muscle_group': target_muscle,
                    'difficulty': difficulty,
                    'instructions': instructions,
                    'equipment_required': equipment_req,
                    'image_url': '/static/images/exercises/barbell-deadlift.jpg',
                    'is_active': True
                }).execute()

                log_audit(session['user']['id'], 'admin', 'EXERCISE_CREATE', 'exercise_library', None, {'name': name})
                flash(f"Exercise '{name}' added to library.", 'success')
            except Exception as e:
                flash(f"Error creating exercise: {str(e)}", 'danger')
        else:
            flash(f"Exercise '{name}' added to library (Config mode).", 'info')
        return redirect(url_for('admin.exercises'))

    exercises_list = GymRepository.get_exercise_library()
    return render_template('admin/exercises.html', exercises=exercises_list)

@admin_bp.route('/exercises/archive/<exercise_id>', methods=['POST'])
def archive_exercise(exercise_id):
    if db_service.is_configured:
        try:
            db_service.get_table('exercise_library').update({'is_archived': True, 'is_active': False}).eq('id', exercise_id).execute()
            log_audit(session['user']['id'], 'admin', 'EXERCISE_ARCHIVE', 'exercise_library', exercise_id)
            flash('Exercise archived successfully.', 'info')
        except Exception as e:
            flash(f"Error archiving exercise: {str(e)}", 'danger')
    return redirect(url_for('admin.exercises'))

@admin_bp.route('/exercises/edit/<exercise_id>', methods=['POST'])
def edit_exercise(exercise_id):
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'Strength')
    target_muscle = request.form.get('target_muscle_group', '')
    difficulty = request.form.get('difficulty', 'Intermediate')
    instructions = request.form.get('instructions', '')
    equipment_req = request.form.get('equipment_required', '')

    data = {
        'name': name,
        'category': category,
        'target_muscle_group': target_muscle,
        'difficulty': difficulty,
        'instructions': instructions,
        'equipment_required': equipment_req
    }
    try:
        GymRepository.update_exercise(exercise_id, data)
        log_audit(session['user']['id'], 'admin', 'EXERCISE_UPDATE', 'exercise_library', exercise_id, data)
        flash(f"Exercise movement '{name}' updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating exercise: {str(e)}", 'danger')
    return redirect(url_for('admin.exercises'))

# =============================================================================
# 10. GYM SERVICES MANAGEMENT (FULL CRUD & HOMEPAGE SYNC)
# =============================================================================
@admin_bp.route('/services', methods=['GET', 'POST'])
def services():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Strength')
        description = request.form.get('description', '')
        benefits_raw = request.form.get('benefits', '')
        benefits = [b.strip() for b in benefits_raw.split('\n') if b.strip()]
        sort_order = int(request.form.get('sort_order', 0))
        is_published = request.form.get('is_published') == 'on'

        slug = name.lower().replace(' ', '-').replace('&', 'and')

        service_data = {
            'name': name,
            'slug': slug,
            'category': category,
            'description': description,
            'benefits': benefits,
            'sort_order': sort_order,
            'is_published': is_published,
            'image_url': '/static/images/programmes/strength-base.jpg'
        }

        try:
            created = GymRepository.create_service(service_data)
            log_audit(session['user']['id'], 'admin', 'SERVICE_CREATE', 'services', created.get('id') if created else None, {'name': name})
            flash(f"Gym Service '{name}' created successfully.", 'success')
        except Exception as e:
            flash(f"Error creating gym service: {str(e)}", 'danger')
        return redirect(url_for('admin.services'))

    services_list = GymRepository.get_all_services(include_archived=True)
    programmes_list = GymRepository.get_all_trainer_programmes()
    return render_template('admin/services.html', services=services_list, programmes=programmes_list)

@admin_bp.route('/services/programmes/<prog_id>/approve', methods=['POST'])
def approve_programme(prog_id):
    GymRepository.update_programme_approval(prog_id, 'approved', True, 'Approved and published by administration.')
    log_audit(session['user']['id'], 'admin', 'PROGRAMME_APPROVE', 'trainer_programmes', prog_id)
    flash('Trainer coaching programme approved and published to public catalog.', 'success')
    return redirect(url_for('admin.services'))

@admin_bp.route('/services/programmes/<prog_id>/reject', methods=['POST'])
def reject_programme(prog_id):
    reason = request.form.get('reason', 'Curriculum does not meet facility standards.')
    GymRepository.update_programme_approval(prog_id, 'rejected', False, reason)
    log_audit(session['user']['id'], 'admin', 'PROGRAMME_REJECT', 'trainer_programmes', prog_id, {'reason': reason})
    flash('Trainer programme proposal rejected.', 'warning')
    return redirect(url_for('admin.services'))

@admin_bp.route('/services/update/<service_id>', methods=['POST'])
def update_service(service_id):
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'Strength')
    description = request.form.get('description', '')
    sort_order = int(request.form.get('sort_order', 0))
    is_published = request.form.get('is_published') == 'on'

    data = {
        'name': name,
        'category': category,
        'description': description,
        'sort_order': sort_order,
        'is_published': is_published
    }

    try:
        GymRepository.update_service(service_id, data)
        log_audit(session['user']['id'], 'admin', 'SERVICE_UPDATE', 'services', service_id, data)
        flash(f"Service '{name}' updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating service: {str(e)}", 'danger')
    return redirect(url_for('admin.services'))

@admin_bp.route('/services/archive/<service_id>', methods=['POST'])
def archive_service(service_id):
    GymRepository.archive_service(service_id)
    log_audit(session['user']['id'], 'admin', 'SERVICE_ARCHIVE', 'services', service_id)
    flash('Service archived and removed from public homepage.', 'info')
    return redirect(url_for('admin.services'))

# =============================================================================
# 11. EQUIPMENT & MAINTENANCE MANAGEMENT
# =============================================================================
@admin_bp.route('/equipment', methods=['GET', 'POST'])
def equipment():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'register_equipment':
            name = request.form.get('name', '').strip()
            category = request.form.get('category', 'Free Weights')
            condition = request.form.get('condition', 'excellent')
            location = request.form.get('location', '')
            notes = request.form.get('notes', '')

            if db_service.is_configured:
                try:
                    res = db_service.get_table('gym_equipment').insert({
                        'name': name,
                        'category': category,
                        'condition': condition,
                        'location': location,
                        'notes': notes,
                        'image_url': '/static/images/equipment/power-cage.jpg',
                        'is_available': True,
                        'acquisition_date': datetime.date.today().isoformat()
                    }).execute()
                    log_audit(session['user']['id'], 'admin', 'EQUIPMENT_REGISTER', 'gym_equipment', res.data[0]['id'] if res.data else None, {'name': name})
                    flash(f"Equipment '{name}' registered in inventory.", 'success')
                except Exception as e:
                    flash(f"Error registering equipment: {str(e)}", 'danger')
            else:
                flash(f"Equipment '{name}' registered (Config mode).", 'info')

        elif action == 'log_maintenance':
            eq_id = request.form.get('equipment_id')
            issue = request.form.get('issue_description', '').strip()
            action_taken = request.form.get('action_taken', '').strip()
            status = request.form.get('status', 'resolved')
            cost = float(request.form.get('cost', 0.0))

            if db_service.is_configured:
                try:
                    db_service.get_table('equipment_maintenance').insert({
                        'equipment_id': eq_id,
                        'reported_by': session['user']['id'],
                        'issue_description': issue,
                        'action_taken': action_taken,
                        'status': status,
                        'cost': cost,
                        'service_date': datetime.date.today().isoformat()
                    }).execute()
                    log_audit(session['user']['id'], 'admin', 'MAINTENANCE_RECORD', 'equipment_maintenance', eq_id, {'cost': cost})
                    flash('Maintenance record logged successfully.', 'success')
                except Exception as e:
                    flash(f"Error logging maintenance: {str(e)}", 'danger')
            else:
                flash('Maintenance record logged (Config mode).', 'info')

        return redirect(url_for('admin.equipment'))

    equipment_list = GymRepository.get_all_equipment()
    maintenance_logs = GymRepository.get_equipment_maintenance_logs()
    return render_template('admin/equipment.html', equipment=equipment_list, maintenance_logs=maintenance_logs)

# =============================================================================
# 12. COMMUNITY HUB MANAGEMENT
# =============================================================================
@admin_bp.route('/community')
def community():
    posts = GymRepository.get_community_posts()
    groups = GymRepository.get_community_groups()
    reports = GymRepository.get_community_reports()
    return render_template('admin/community.html', posts=posts, groups=groups, reports=reports)

@admin_bp.route('/community/hide-post/<post_id>', methods=['POST'])
def hide_community_post(post_id):
    reason = request.form.get('reason', 'Administrative moderation')
    if db_service.is_configured:
        try:
            db_service.get_table('community_posts').update({'is_hidden': True}).eq('id', post_id).execute()
            log_audit(session['user']['id'], 'admin', 'COMMUNITY_POST_HIDE', 'community_posts', post_id, reason=reason)
            flash('Post hidden from community feed.', 'warning')
        except Exception as e:
            flash(f"Error hiding post: {str(e)}", 'danger')
    return redirect(url_for('admin.community'))

@admin_bp.route('/community/unhide-post/<post_id>', methods=['POST'])
def unhide_community_post(post_id):
    try:
        GymRepository.unhide_community_post(post_id)
        log_audit(session['user']['id'], 'admin', 'COMMUNITY_POST_UNHIDE', 'community_posts', post_id)
        flash('Post restored to community feed.', 'success')
    except Exception as e:
        flash(f"Error unhiding post: {str(e)}", 'danger')
    return redirect(url_for('admin.community'))

@admin_bp.route('/community/delete-post/<post_id>', methods=['POST'])
def delete_community_post(post_id):
    try:
        GymRepository.delete_community_post(post_id)
        log_audit(session['user']['id'], 'admin', 'COMMUNITY_POST_DELETE', 'community_posts', post_id)
        flash('Post permanently removed from community feed.', 'info')
    except Exception as e:
        flash(f"Error deleting post: {str(e)}", 'danger')
    return redirect(url_for('admin.community'))

# =============================================================================
# 13. ANNOUNCEMENTS & NOTIFICATIONS
# =============================================================================
@admin_bp.route('/announcements', methods=['GET', 'POST'])
def announcements():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        target_role = request.form.get('target_role', 'all')
        is_published = request.form.get('is_published') == 'on'

        data = {
            'title': title,
            'content': content,
            'author_id': session['user']['id'],
            'target_role': target_role,
            'is_published': is_published
        }

        try:
            created = GymRepository.create_announcement(data)
            log_audit(session['user']['id'], 'admin', 'ANNOUNCEMENT_CREATE', 'announcements', created.get('id') if created else None, {'title': title})
            flash(f"Announcement '{title}' published.", 'success')
        except Exception as e:
            flash(f"Error publishing announcement: {str(e)}", 'danger')
        return redirect(url_for('admin.announcements'))

    announcements_list = GymRepository.get_all_announcements()
    return render_template('admin/announcements.html', announcements=announcements_list)

@admin_bp.route('/announcements/edit/<announcement_id>', methods=['POST'])
def edit_announcement(announcement_id):
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    target_role = request.form.get('target_role', 'all')
    is_published = request.form.get('is_published') == 'on' or request.form.get('is_published') == 'true'

    data = {
        'title': title,
        'content': content,
        'target_role': target_role,
        'is_published': is_published
    }
    try:
        GymRepository.update_announcement(announcement_id, data)
        log_audit(session['user']['id'], 'admin', 'ANNOUNCEMENT_UPDATE', 'announcements', announcement_id, data)
        flash(f"Announcement '{title}' updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating announcement: {str(e)}", 'danger')
    return redirect(url_for('admin.announcements'))

@admin_bp.route('/announcements/delete/<announcement_id>', methods=['POST'])
def delete_announcement(announcement_id):
    try:
        GymRepository.delete_announcement(announcement_id)
        log_audit(session['user']['id'], 'admin', 'ANNOUNCEMENT_DELETE', 'announcements', announcement_id)
        flash('Announcement removed.', 'info')
    except Exception as e:
        flash(f"Error deleting announcement: {str(e)}", 'danger')
    return redirect(url_for('admin.announcements'))

@admin_bp.route('/notifications', methods=['GET', 'POST'])
def notifications():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        target_role = request.form.get('target_role', 'all')

        success = GymRepository.broadcast_notification(title=title, message=message, notif_type='announcement', target_role=target_role)
        if success:
            log_audit(session['user']['id'], 'admin', 'NOTIFICATION_BROADCAST', 'notifications', None, {'title': title, 'target': target_role})
            flash(f"Notification broadcast sent to '{target_role.upper()}' users.", 'success')
        else:
            flash("Notification recorded (Config mode).", 'info')
        return redirect(url_for('admin.notifications'))

    user_notifs = GymRepository.get_user_notifications(session['user']['id'])
    return render_template('admin/notifications.html', notifications=user_notifs)

@admin_bp.route('/notifications/delete/<notification_id>', methods=['POST'])
def delete_notification(notification_id):
    try:
        GymRepository.delete_notification(notification_id)
        log_audit(session['user']['id'], 'admin', 'NOTIFICATION_DELETE', 'notifications', notification_id)
        flash('Notification deleted.', 'info')
    except Exception as e:
        flash(f"Error deleting notification: {str(e)}", 'danger')
    return redirect(url_for('admin.notifications'))

# =============================================================================
# 14. COMPREHENSIVE REPORTS MODULE (SEPARATE FROM DASHBOARD)
# =============================================================================
@admin_bp.route('/reports')
def reports():
    report_type = request.args.get('type', 'cash_collection')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    data = []
    headers = []
    total_val = None

    if report_type == 'cash_collection':
        headers = ['Receipt #', 'Date & Time', 'Member', 'Amount (KES)', 'Status', 'Recorded By']
        raw = GymRepository.get_all_cash_payments()
        for p in raw:
            p_date = p.get('payment_date', '')[:10]
            if start_date and p_date < start_date: continue
            if end_date and p_date > end_date: continue
            data.append([
                p.get('receipt_number'),
                p.get('payment_date', '')[:16],
                p.get('profiles', {}).get('full_name', 'Member') if p.get('profiles') else 'N/A',
                f"{float(p.get('amount', 0)):,.2f}",
                p.get('status', '').upper(),
                p.get('recorder', {}).get('full_name', 'Staff') if p.get('recorder') else 'Staff'
            ])
        total_val = f"KES {sum(float(p.get('amount', 0)) for p in raw if p.get('status') == 'confirmed'):,.2f}"

    elif report_type == 'attendance':
        headers = ['Check-in Time', 'Athlete Member', 'Verification Status', 'Recorded By', 'Notes']
        raw = GymRepository.get_all_attendance()
        for a in raw:
            a_date = a.get('check_in_time', '')[:10]
            if start_date and a_date < start_date: continue
            if end_date and a_date > end_date: continue
            data.append([
                a.get('check_in_time', '')[:16],
                a.get('profiles', {}).get('full_name', 'Athlete') if a.get('profiles') else 'N/A',
                a.get('status', '').upper(),
                a.get('recorder', {}).get('full_name', 'Front Desk') if a.get('recorder') else 'Reception Desk',
                a.get('notes', '-')
            ])
        total_val = f"{len(data)} Check-ins Recorded"

    elif report_type == 'memberships':
        headers = ['Member', 'Package Plan', 'Status', 'Start Date', 'End Date', 'Renewals']
        raw = GymRepository.get_all_subscriptions()
        for s in raw:
            data.append([
                s.get('profiles', {}).get('full_name', 'Athlete') if s.get('profiles') else 'N/A',
                s.get('membership_plans', {}).get('name', 'Plan') if s.get('membership_plans') else 'Standard',
                s.get('status', '').upper(),
                s.get('start_date', 'Pending'),
                s.get('end_date', 'Pending'),
                s.get('renewal_count', 0)
            ])
        total_val = f"{len(data)} Subscriptions"

    elif report_type == 'trainers':
        headers = ['Trainer Name', 'Email', 'Specialisations', 'Assigned Athletes']
        trainers_raw = GymRepository.get_all_trainers()
        assignments_raw = GymRepository.get_all_trainer_assignments()
        tr_map = {}
        for a in assignments_raw:
            tr_map[a.get('trainer_id')] = tr_map.get(a.get('trainer_id'), 0) + 1
        for t in trainers_raw:
            data.append([
                t.get('full_name'),
                t.get('email'),
                ', '.join(t.get('trainer_details', {}).get('specialisations', [])) if t.get('trainer_details') else 'Strength',
                tr_map.get(t.get('id'), 0)
            ])
        total_val = f"{len(trainers_raw)} Trainers on Staff"

    elif report_type == 'equipment':
        headers = ['Equipment Asset', 'Category', 'Location', 'Condition', 'Operational Status']
        eq_raw = GymRepository.get_all_equipment()
        for eq in eq_raw:
            data.append([
                eq.get('name'),
                eq.get('category'),
                eq.get('location', 'Main Floor'),
                eq.get('condition', 'good').upper(),
                'AVAILABLE' if eq.get('is_available') else 'OUT OF SERVICE'
            ])
        total_val = f"{len(eq_raw)} Equipment Assets"

    # CSV Export Handling
    if request.args.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([f"STRAKLY GYM REPORT — {report_type.upper().replace('_', ' ')}"])
        writer.writerow([f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        writer.writerow([])
        writer.writerow(headers)
        writer.writerows(data)
        if total_val:
            writer.writerow([])
            writer.writerow(['TOTAL / SUMMARY', total_val])

        return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f"attachment; filename=strakly_gym_{report_type}_report.csv"})

    return render_template('admin/reports.html',
                           report_type=report_type,
                           headers=headers,
                           data=data,
                           total_val=total_val,
                           start_date=start_date,
                           end_date=end_date)

# =============================================================================
# 15. AUDIT LOGS (APPEND-ONLY SECURITY TRAIL)
# =============================================================================
@admin_bp.route('/audit-logs')
def audit_logs():
    role_filter = request.args.get('role')
    action_filter = request.args.get('action')
    search = request.args.get('search')

    logs = GymRepository.get_audit_logs(limit=250, role_filter=role_filter, action_filter=action_filter, search=search)
    return render_template('admin/audit_logs.html', logs=logs, role_filter=role_filter, action_filter=action_filter, search=search)

# =============================================================================
# 16. USER ACCOUNTS & ACCESS CONTROL
# =============================================================================
@admin_bp.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        role = request.form.get('role', 'member')
        phone = request.form.get('phone', '').strip()

        try:
            GymRepository.create_user_account(full_name, email, role, phone)
            log_audit(session['user']['id'], 'admin', 'USER_CREATE', 'profiles', None, {'name': full_name, 'email': email, 'role': role})
            flash(f"User account '{email}' ({role.upper()}) created successfully.", 'success')
        except Exception as e:
            flash(f"Error creating user account: {str(e)}", 'danger')
        return redirect(url_for('admin.users'))

    users_list = GymRepository.get_all_user_accounts()
    return render_template('admin/users.html', users=users_list)

@admin_bp.route('/users/delete/<user_id>', methods=['POST'])
def delete_user(user_id):
    if user_id == session['user']['id']:
        flash('Cannot delete your own active session account.', 'danger')
        return redirect(url_for('admin.users'))
    try:
        GymRepository.delete_user_account(user_id)
        log_audit(session['user']['id'], 'admin', 'USER_DELETE', 'profiles', user_id)
        flash('User account deactivated and archived safely. Historical financial and training records preserved.', 'info')
    except Exception as e:
        flash(f"Error deleting user: {str(e)}", 'danger')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/update-role/<user_id>', methods=['POST'])
def update_user_role(user_id):
    new_role = request.form.get('role')
    if new_role not in ['admin', 'trainer', 'member']:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin.users'))

    try:
        GymRepository.update_user_role(user_id, new_role)
        log_audit(session['user']['id'], 'admin', 'USER_ROLE_CHANGE', 'profiles', user_id, {'new_role': new_role})
        flash(f"User role updated to '{new_role.upper()}'.", 'success')
    except Exception as e:
        flash(f"Error updating user role: {str(e)}", 'danger')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/toggle-active/<user_id>', methods=['POST'])
def toggle_user_active(user_id):
    status_str = request.form.get('is_active', 'false')
    is_active = (status_str == 'true')

    try:
        GymRepository.toggle_user_active(user_id, is_active)
        action_name = 'USER_ACTIVATE' if is_active else 'USER_DEACTIVATE'
        log_audit(session['user']['id'], 'admin', action_name, 'profiles', user_id)
        flash(f"User account {'activated' if is_active else 'deactivated'}.", 'info')
    except Exception as e:
        flash(f"Error updating user status: {str(e)}", 'danger')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/edit/<user_id>', methods=['POST'])
def edit_user(user_id):
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    role = request.form.get('role', 'member')

    data = {
        'full_name': full_name,
        'phone': phone,
        'role': role
    }
    try:
        GymRepository.update_user_account(user_id, data)
        log_audit(session['user']['id'], 'admin', 'USER_EDIT', 'profiles', user_id, data)
        flash(f"User account '{full_name}' updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating user account: {str(e)}", 'danger')
    return redirect(url_for('admin.users'))

# =============================================================================
# 17. GYM & SYSTEM SETTINGS
# =============================================================================
@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        name = request.form.get('gym_name', '').strip()
        tagline = request.form.get('tagline', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        receipt_footer = request.form.get('receipt_footer', '').strip()
        currency = request.form.get('currency', 'KES')

        new_settings = {
            'gym_name': name,
            'tagline': tagline,
            'address': address,
            'phone': phone,
            'email': email,
            'currency': currency,
            'receipt_footer': receipt_footer,
            'opening_hours': {
                'weekdays': request.form.get('hours_weekdays', '05:00 AM - 10:00 PM'),
                'saturdays': request.form.get('hours_saturdays', '06:00 AM - 09:00 PM'),
                'sundays': request.form.get('hours_sundays', '07:00 AM - 07:00 PM'),
                'holidays': request.form.get('hours_holidays', '08:00 AM - 05:00 PM')
            }
        }
        GymRepository.update_setting('general', new_settings)
        log_audit(session['user']['id'], 'admin', 'SETTINGS_UPDATE', 'platform_settings', 'general', new_settings)
        flash('Platform brand and facility settings saved successfully.', 'success')
        return redirect(url_for('admin.settings'))

    current_settings = GymRepository.get_setting('general', {})
    return render_template('admin/settings.html', settings=current_settings)
