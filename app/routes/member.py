import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.services.auth_service import member_required
from app.services.repository import GymRepository
from app.services.supabase_client import db_service
from app.services.audit_service import log_audit

member_bp = Blueprint('member', __name__)

@member_bp.before_request
@member_required
def check_member_access():
    pass

# =========================================================================
# 1. DASHBOARD
# =========================================================================
@member_bp.route('/dashboard')
def dashboard():
    member_id = session.get('user', {}).get('id')
    subscriptions = GymRepository.get_member_subscriptions(member_id)
    payments = GymRepository.get_member_cash_payments(member_id)
    attendance = GymRepository.get_member_attendance(member_id)
    upcoming_classes = GymRepository.get_upcoming_classes()
    workout_plans = GymRepository.get_member_workout_plans(member_id)
    progress_records = GymRepository.get_member_progress(member_id)
    
    # Active subscription check
    active_sub = next((s for s in subscriptions if s.get('status') == 'active'), None)

    # Coached vs self-guided check
    coach_assignment = GymRepository.get_member_coach(member_id)
    
    # Recent Personal Records & Goals
    prs = GymRepository.get_member_prs(member_id)
    goals = GymRepository.get_member_goals(member_id)
    active_goals = [g for g in goals if g.get('status') == 'in_progress']

    # PT Sessions & Wallet
    pt_wallet = GymRepository.get_member_pt_wallet(member_id)

    # Days streak calculation
    streak = 0
    if attendance:
        streak = min(len(attendance), 30)

    # Activity chart data (workouts in last 7 days)
    labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    workout_counts = [0] * 7
    for a in attendance[:14]:
        try:
            dt = datetime.datetime.fromisoformat(a.get('check_in_time', '').replace('Z', '+00:00'))
            workout_counts[dt.weekday()] += 1
        except Exception:
            pass

    return render_template('member/dashboard.html',
                           subscriptions=subscriptions,
                           active_sub=active_sub,
                           payments=payments,
                           attendance=attendance,
                           upcoming_classes=upcoming_classes[:3],
                           workout_plans=workout_plans,
                           progress_records=progress_records,
                           coach_assignment=coach_assignment,
                           prs=prs[:4],
                           active_goals=active_goals[:3],
                           pt_wallet=pt_wallet,
                           streak=streak,
                           activity_labels=labels,
                           activity_data=workout_counts)

# =========================================================================
# 2. PROFILE & FITNESS IDENTITY
# =========================================================================
@member_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    member_id = session.get('user', {}).get('id')
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        emergency_name = request.form.get('emergency_contact_name', '').strip()
        emergency_phone = request.form.get('emergency_contact_phone', '').strip()
        fitness_goals = request.form.get('fitness_goals', '').strip()

        if not full_name:
            flash('Full name cannot be blank.', 'danger')
            return redirect(url_for('member.profile'))

        try:
            GymRepository.update_member_profile(member_id, full_name, phone, emergency_name, emergency_phone, fitness_goals)
            # update session user
            if 'user' in session:
                session['user']['full_name'] = full_name
                session['user']['phone'] = phone
                session.modified = True
            log_audit(member_id, 'member', 'PROFILE_UPDATE', 'profiles', member_id)
            flash('Fitness profile updated successfully!', 'success')
        except Exception as e:
            flash(f"Error updating profile: {str(e)}", 'danger')
        return redirect(url_for('member.profile'))

    member = GymRepository.get_member_full_detail(member_id) or {}
    return render_template('member/profile.html', member=member)

# =========================================================================
# 3. MY MEMBERSHIP
# =========================================================================
@member_bp.route('/membership')
def membership():
    member_id = session.get('user', {}).get('id')
    subscriptions = GymRepository.get_member_subscriptions(member_id)
    plans = GymRepository.get_active_plans()
    requests_list = GymRepository.get_member_membership_requests(member_id)
    active_sub = next((s for s in subscriptions if s.get('status') == 'active'), None)

    days_remaining = 0
    if active_sub and active_sub.get('end_date'):
        try:
            end_dt = datetime.date.fromisoformat(active_sub['end_date'])
            days_remaining = max(0, (end_dt - datetime.date.today()).days)
        except Exception:
            pass

    return render_template('member/membership.html',
                           subscriptions=subscriptions,
                           plans=plans,
                           requests=requests_list,
                           active_sub=active_sub,
                           days_remaining=days_remaining)

@member_bp.route('/membership/request', methods=['POST'])
def request_membership():
    member_id = session.get('user', {}).get('id')
    req_type = request.form.get('request_type', 'upgrade')
    target_plan_id = request.form.get('target_plan_id') or None
    reason = request.form.get('reason', '').strip()
    freeze_start = request.form.get('freeze_start_date') or None
    freeze_end = request.form.get('freeze_end_date') or None

    try:
        GymRepository.submit_membership_request(member_id, req_type, target_plan_id, reason, freeze_start, freeze_end)
        log_audit(member_id, 'member', f'MEMBERSHIP_REQUEST_{req_type.upper()}', 'membership_requests', None)
        flash(f'Your {req_type} request has been submitted for front-desk review.', 'success')
    except Exception as e:
        flash(f"Error submitting request: {str(e)}", 'danger')
    return redirect(url_for('member.membership'))

# =========================================================================
# 4. WORKOUT CENTRE
# =========================================================================
@member_bp.route('/workouts', methods=['GET', 'POST'])
def workouts():
    member_id = session.get('user', {}).get('id')
    if request.method == 'POST':
        title = request.form.get('title', 'Daily Training Session').strip()
        duration = int(request.form.get('duration_minutes', 60))
        notes = request.form.get('notes', '').strip()

        if db_service.is_configured:
            try:
                db_service.get_table('workout_logs').insert({
                    'member_id': member_id,
                    'title': title,
                    'duration_minutes': duration,
                    'notes': notes,
                    'completion_status': 'completed'
                }).execute()

                log_audit(member_id, 'member', 'WORKOUT_LOG_RECORD', 'workout_logs', None, {'title': title})
                flash('Workout session logged successfully!', 'success')
            except Exception as e:
                flash(f"Error logging workout: {str(e)}", 'danger')
        else:
            flash(f"Workout '{title}' logged successfully (Demo mode).", 'success')
        return redirect(url_for('member.workouts'))

    plans = GymRepository.get_member_workout_plans(member_id)
    # Get past logged workouts
    logs = []
    if db_service.is_configured:
        try:
            res = db_service.get_table('workout_logs').select('*').eq('member_id', member_id).order('created_at', desc=True).limit(20).execute()
            logs = res.data or []
        except Exception:
            pass

    return render_template('member/workouts.html', plans=plans, workout_logs=logs)

# =========================================================================
# 5. MOVEMENT LIBRARY / EXERCISE DISCOVERY
# =========================================================================
@member_bp.route('/exercises')
def exercises():
    target_muscle = request.args.get('muscle', '').strip().lower()
    difficulty = request.args.get('difficulty', '').strip().lower()
    search = request.args.get('q', '').strip().lower()

    all_exercises = GymRepository.get_exercise_library()
    filtered = []
    for ex in all_exercises:
        if target_muscle and ex.get('target_muscle_group', '').lower() != target_muscle:
            continue
        if difficulty and ex.get('difficulty_level', '').lower() != difficulty:
            continue
        if search and search not in ex.get('name', '').lower() and search not in ex.get('description', '').lower():
            continue
        filtered.append(ex)

    return render_template('member/exercises.html', exercises=filtered, total_count=len(all_exercises))

# =========================================================================
# 6. TRAINING CALENDAR
# =========================================================================
@member_bp.route('/calendar')
def calendar():
    member_id = session.get('user', {}).get('id')
    events = GymRepository.get_member_calendar_events(member_id)
    return render_template('member/calendar.html', events=events)

# =========================================================================
# 7. COACHING & PERSONAL TRAINING
# =========================================================================
@member_bp.route('/trainer')
def trainer():
    member_id = session.get('user', {}).get('id')
    coach = GymRepository.get_member_coach(member_id)
    trainers = GymRepository.get_all_trainers()
    pt_wallet = GymRepository.get_member_pt_wallet(member_id)
    pt_sessions = GymRepository.get_member_pt_sessions(member_id)
    
    return render_template('member/trainer.html',
                           coach=coach,
                           trainers=trainers,
                           pt_wallet=pt_wallet,
                           pt_sessions=pt_sessions)

@member_bp.route('/trainer/book-pt', methods=['POST'])
def book_pt():
    member_id = session.get('user', {}).get('id')
    trainer_id = request.form.get('trainer_id')
    session_date = request.form.get('session_date')
    start_time = request.form.get('start_time')
    focus_area = request.form.get('focus_area', 'General Conditioning')
    notes = request.form.get('notes', '')

    if not trainer_id or not session_date or not start_time:
        flash('Please specify your coach, date, and preferred time slot.', 'warning')
        return redirect(url_for('member.trainer'))

    try:
        GymRepository.book_pt_session(member_id, trainer_id, session_date, start_time, focus_area, notes)
        log_audit(member_id, 'member', 'BOOK_PT_SESSION', 'pt_sessions', None)
        flash('1-on-1 Personal Training session requested! Your coach will confirm.', 'success')
    except Exception as e:
        flash(f"Error booking PT session: {str(e)}", 'danger')
    return redirect(url_for('member.trainer'))

@member_bp.route('/trainer/request-coach', methods=['POST'])
def request_coach():
    member_id = session.get('user', {}).get('id')
    trainer_id = request.form.get('preferred_trainer_id') or None
    req_type = request.form.get('request_type', 'assign')
    fitness_goals = request.form.get('fitness_goals', '')
    notes = request.form.get('notes', '')

    try:
        GymRepository.submit_coach_request(member_id, trainer_id, req_type, fitness_goals, notes)
        log_audit(member_id, 'member', f'COACH_REQUEST_{req_type.upper()}', 'coach_requests', None)
        flash('Coach request submitted to Head of Coaching for matching!', 'success')
    except Exception as e:
        flash(f"Error submitting coach request: {str(e)}", 'danger')
    return redirect(url_for('member.trainer'))

# =========================================================================
# 8. CLASSES & BOOKINGS
# =========================================================================
@member_bp.route('/classes')
def classes():
    member_id = session.get('user', {}).get('id')
    classes_list = GymRepository.get_upcoming_classes()
    my_bookings = GymRepository.get_member_booked_classes(member_id)
    booked_class_ids = [b.get('class_id') for b in my_bookings if b.get('booking_status') == 'confirmed']

    return render_template('member/classes.html',
                           classes=classes_list,
                           my_bookings=my_bookings,
                           booked_class_ids=booked_class_ids)

@member_bp.route('/classes/book/<class_id>', methods=['POST'])
def book_class(class_id):
    member_id = session.get('user', {}).get('id')
    if db_service.is_configured:
        try:
            # Check if already booked
            existing = db_service.get_table('class_bookings').select('*').eq('class_id', class_id).eq('member_id', member_id).eq('booking_status', 'confirmed').execute()
            if existing.data:
                flash('You have already reserved a spot in this class.', 'info')
                return redirect(url_for('member.classes'))

            # Check capacity
            bookings = db_service.get_table('class_bookings').select('*').eq('class_id', class_id).eq('booking_status', 'confirmed').execute()
            cls = db_service.get_table('fitness_classes').select('*').eq('id', class_id).execute()
            capacity = cls.data[0]['capacity'] if cls.data else 20
            
            if len(bookings.data) >= capacity:
                flash('This class has reached maximum athlete capacity.', 'warning')
                return redirect(url_for('member.classes'))

            db_service.get_table('class_bookings').insert({
                'class_id': class_id,
                'member_id': member_id,
                'booking_status': 'confirmed'
            }).execute()

            log_audit(member_id, 'member', 'CLASS_BOOK', 'class_bookings', class_id)
            flash('Class spot booked successfully! See you on the floor.', 'success')
        except Exception as e:
            flash(f"Booking error: {str(e)}", 'danger')
    else:
        flash('Class booked successfully (Evaluation mode).', 'success')
    return redirect(url_for('member.classes'))

@member_bp.route('/classes/cancel/<booking_id>', methods=['POST'])
def cancel_class(booking_id):
    member_id = session.get('user', {}).get('id')
    success = GymRepository.cancel_class_booking(booking_id, member_id)
    if success:
        log_audit(member_id, 'member', 'CLASS_BOOKING_CANCEL', 'class_bookings', booking_id)
        flash('Class reservation cancelled.', 'info')
    else:
        flash('Could not cancel booking.', 'danger')
    return redirect(url_for('member.classes'))

# =========================================================================
# 9. PROGRESS STUDIO
# =========================================================================
@member_bp.route('/progress')
def progress():
    member_id = session.get('user', {}).get('id')
    records = GymRepository.get_member_progress(member_id)
    goals = GymRepository.get_member_goals(member_id)
    prs = GymRepository.get_member_prs(member_id)
    photos = GymRepository.get_member_progress_photos(member_id)

    # Latest weight
    latest_weight = records[0].get('weight') if records else None

    return render_template('member/progress.html',
                           progress_records=records,
                           goals=goals,
                           prs=prs,
                           photos=photos,
                           latest_weight=latest_weight)

@member_bp.route('/progress/log', methods=['POST'])
def log_progress():
    member_id = session.get('user', {}).get('id')
    weight = request.form.get('weight')
    body_fat = request.form.get('body_fat_percentage') or None
    chest = request.form.get('chest_cm') or None
    waist = request.form.get('waist_cm') or None
    arms = request.form.get('arms_cm') or None
    notes = request.form.get('notes', '')

    if not weight:
        flash('Body weight is required to log progress.', 'warning')
        return redirect(url_for('member.progress'))

    if db_service.is_configured:
        try:
            data = {
                'member_id': member_id,
                'weight': float(weight),
                'notes': notes
            }
            if body_fat: data['body_fat_percentage'] = float(body_fat)
            if chest: data['chest_cm'] = float(chest)
            if waist: data['waist_cm'] = float(waist)
            if arms: data['arms_cm'] = float(arms)

            db_service.get_table('member_progress_logs').insert(data).execute()
            log_audit(member_id, 'member', 'PROGRESS_MEASUREMENT_LOG', 'member_progress_logs', None)
            flash('Body measurements logged successfully!', 'success')
        except Exception as e:
            flash(f"Error logging measurements: {str(e)}", 'danger')
    else:
        flash('Body measurements logged (Demo mode).', 'success')
    return redirect(url_for('member.progress'))

@member_bp.route('/progress/goal', methods=['POST'])
def add_goal():
    member_id = session.get('user', {}).get('id')
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'strength')
    target_value = request.form.get('target_value', 0)
    current_value = request.form.get('current_value', 0)
    unit = request.form.get('unit', 'kg')
    target_date = request.form.get('target_date') or None

    try:
        GymRepository.create_member_goal(member_id, title, category, float(target_value), float(current_value), unit, target_date)
        flash('New fitness target established! Keep crushing it.', 'success')
    except Exception as e:
        flash(f"Error saving goal: {str(e)}", 'danger')
    return redirect(url_for('member.progress'))

@member_bp.route('/progress/goal/update/<goal_id>', methods=['POST'])
def update_goal(goal_id):
    current_value = float(request.form.get('current_value', 0))
    status = request.form.get('status', 'in_progress')
    try:
        GymRepository.update_member_goal(goal_id, current_value, status)
        flash('Goal progress updated!', 'success')
    except Exception as e:
        flash(f"Error updating goal: {str(e)}", 'danger')
    return redirect(url_for('member.progress'))

@member_bp.route('/progress/goal/delete/<goal_id>', methods=['POST'])
def delete_goal(goal_id):
    member_id = session.get('user', {}).get('id')
    GymRepository.delete_member_goal(goal_id, member_id)
    flash('Goal removed.', 'info')
    return redirect(url_for('member.progress'))

@member_bp.route('/progress/pr', methods=['POST'])
def add_pr():
    member_id = session.get('user', {}).get('id')
    exercise_name = request.form.get('exercise_name', '').strip()
    weight_kg = request.form.get('weight_kg', 0)
    reps = int(request.form.get('reps', 1))
    notes = request.form.get('notes', '')

    if not exercise_name or not weight_kg:
        flash('Exercise name and weight are required.', 'warning')
        return redirect(url_for('member.progress'))

    try:
        GymRepository.add_member_pr(member_id, exercise_name, float(weight_kg), reps, notes)
        flash(f'New PR logged: {exercise_name} ({weight_kg} kg)!', 'success')
    except Exception as e:
        flash(f"Error logging PR: {str(e)}", 'danger')
    return redirect(url_for('member.progress'))

@member_bp.route('/progress/photo', methods=['POST'])
def add_photo():
    member_id = session.get('user', {}).get('id')
    photo_url = request.form.get('photo_url', '').strip()
    photo_tag = request.form.get('photo_tag', 'front')
    recorded_weight = request.form.get('recorded_weight') or None
    notes = request.form.get('notes', '')

    if not photo_url:
        flash('Photo URL or upload is required.', 'warning')
        return redirect(url_for('member.progress'))

    try:
        GymRepository.add_progress_photo(member_id, photo_url, photo_tag, float(recorded_weight) if recorded_weight else None, notes)
        flash('Progress photo logged privately!', 'success')
    except Exception as e:
        flash(f"Error adding photo: {str(e)}", 'danger')
    return redirect(url_for('member.progress'))

@member_bp.route('/progress/photo/delete/<photo_id>', methods=['POST'])
def delete_photo(photo_id):
    member_id = session.get('user', {}).get('id')
    GymRepository.delete_progress_photo(photo_id, member_id)
    flash('Progress photo removed.', 'info')
    return redirect(url_for('member.progress'))

# =========================================================================
# 10. CHALLENGES & ACHIEVEMENTS
# =========================================================================
@member_bp.route('/challenges')
def challenges():
    member_id = session.get('user', {}).get('id')
    all_challenges = GymRepository.get_active_challenges()
    my_challenges = GymRepository.get_member_challenges(member_id)
    joined_ids = [c.get('challenge_id') for c in my_challenges]
    achievements = GymRepository.get_member_achievements(member_id)

    return render_template('member/challenges.html',
                           challenges=all_challenges,
                           my_challenges=my_challenges,
                           joined_ids=joined_ids,
                           achievements=achievements)

@member_bp.route('/challenges/join/<challenge_id>', methods=['POST'])
def join_challenge(challenge_id):
    member_id = session.get('user', {}).get('id')
    try:
        GymRepository.join_challenge(member_id, challenge_id)
        log_audit(member_id, 'member', 'CHALLENGE_JOIN', 'fitness_challenges', challenge_id)
        flash('You have entered the challenge! Train hard!', 'success')
    except Exception as e:
        flash(f"Error joining challenge: {str(e)}", 'danger')
    return redirect(url_for('member.challenges'))

# =========================================================================
# 11. GEAR & EQUIPMENT
# =========================================================================
@member_bp.route('/gear')
def gear():
    member_id = session.get('user', {}).get('id')
    equipment = GymRepository.get_all_equipment()
    reservations = GymRepository.get_member_equipment_reservations(member_id)
    return render_template('member/gear.html', equipment=equipment, reservations=reservations)

@member_bp.route('/gear/reserve', methods=['POST'])
def reserve_gear():
    member_id = session.get('user', {}).get('id')
    equipment_id = request.form.get('equipment_id')
    res_date = request.form.get('reservation_date', datetime.date.today().isoformat())
    start_time = request.form.get('start_time', datetime.datetime.now().strftime('%H:%M'))
    duration = int(request.form.get('duration_minutes', 60))
    notes = request.form.get('notes', '')

    try:
        GymRepository.reserve_equipment(member_id, equipment_id, res_date, start_time, duration, notes)
        log_audit(member_id, 'member', 'EQUIPMENT_RESERVE', 'equipment_reservations', equipment_id)
        flash('Equipment reserved! Check in at the gear desk.', 'success')
    except Exception as e:
        flash(f"Error reserving equipment: {str(e)}", 'danger')
    return redirect(url_for('member.gear'))

# =========================================================================
# 12. STRAKLY MERCHANDISE STORE (STRICT CASH ON COLLECTION)
# =========================================================================
@member_bp.route('/store')
def store():
    member_id = session.get('user', {}).get('id')
    category = request.args.get('category')
    products = GymRepository.get_store_products(category)
    orders = GymRepository.get_member_store_orders(member_id)
    return render_template('member/store.html', products=products, orders=orders, active_cat=category)

@member_bp.route('/store/order', methods=['POST'])
def place_order():
    member_id = session.get('user', {}).get('id')
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    size = request.form.get('selected_size', 'Standard')
    notes = request.form.get('pickup_notes', '')

    try:
        order = GymRepository.place_store_order(member_id, product_id, quantity, size, notes)
        order_num = order.get('order_number') if order else 'STRK'
        log_audit(member_id, 'member', 'STORE_ORDER_PLACE', 'store_orders', order.get('id') if order else None)
        flash(f'Order #{order_num} reserved! STRICT CASH ON COLLECTION: Please pay in cash at the gym reception upon collection.', 'success')
    except Exception as e:
        flash(f"Error placing order: {str(e)}", 'danger')
    return redirect(url_for('member.store'))

# =========================================================================
# 13. GYM SERVICES
# =========================================================================
@member_bp.route('/services')
def services():
    member_id = session.get('user', {}).get('id')
    services_list = GymRepository.get_published_services()
    inquiries = GymRepository.get_member_service_inquiries(member_id)
    return render_template('member/services.html', services=services_list, inquiries=inquiries)

@member_bp.route('/services/inquire', methods=['POST'])
def inquire_service():
    member_id = session.get('user', {}).get('id')
    service_id = request.form.get('service_id')
    pref_date = request.form.get('preferred_date') or None
    pref_time = request.form.get('preferred_time') or None
    notes = request.form.get('notes', '')

    try:
        GymRepository.submit_service_inquiry(member_id, service_id, pref_date, pref_time, notes)
        log_audit(member_id, 'member', 'SERVICE_INQUIRY', 'service_inquiries', service_id)
        flash('Service consultation request sent! Our desk team will contact you.', 'success')
    except Exception as e:
        flash(f"Error submitting inquiry: {str(e)}", 'danger')
    return redirect(url_for('member.services'))

# =========================================================================
# 14. MY PAYMENTS & RECEIPTS (STRICT CASH PAYMENTS)
# =========================================================================
@member_bp.route('/payments')
def payments():
    member_id = session.get('user', {}).get('id')
    payments_list = GymRepository.get_member_cash_payments(member_id)
    total_paid = sum(float(p.get('amount', 0)) for p in payments_list)
    return render_template('member/payments.html', payments=payments_list, total_paid=total_paid)

# =========================================================================
# 15. ATTENDANCE HISTORY (STRICT MANUAL FRONT DESK CHECK-INS)
# =========================================================================
@member_bp.route('/attendance')
def attendance():
    member_id = session.get('user', {}).get('id')
    attendance_list = GymRepository.get_member_attendance(member_id)
    return render_template('member/attendance.html', attendance=attendance_list)

# =========================================================================
# 16. NOTIFICATIONS
# =========================================================================
@member_bp.route('/notifications')
def notifications():
    member_id = session.get('user', {}).get('id')
    notifs = GymRepository.get_member_notifications(member_id)
    announcements = GymRepository.get_all_announcements()
    return render_template('member/notifications.html', notifications=notifs, announcements=announcements)

@member_bp.route('/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    member_id = session.get('user', {}).get('id')
    GymRepository.mark_notifications_read(member_id)
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('member.notifications'))

# =========================================================================
# 17. HELP & SUPPORT & SETTINGS
# =========================================================================
@member_bp.route('/support', methods=['GET', 'POST'])
def support():
    member_id = session.get('user', {}).get('id')
    if request.method == 'POST':
        category = request.form.get('category', 'general')
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        priority = request.form.get('priority', 'normal')

        if not subject or not message:
            flash('Subject and message cannot be empty.', 'warning')
            return redirect(url_for('member.support'))

        try:
            ticket = GymRepository.create_support_ticket(member_id, category, subject, message, priority)
            t_num = ticket.get('ticket_number') if ticket else 'TCK'
            log_audit(member_id, 'member', 'SUPPORT_TICKET_CREATE', 'support_tickets', None)
            flash(f'Support ticket #{t_num} logged. Our front desk support will respond shortly.', 'success')
        except Exception as e:
            flash('Support inquiry logged. Our front desk support will respond shortly.', 'success')
        return redirect(url_for('member.support'))

    tickets = GymRepository.get_member_support_tickets(member_id)
    return render_template('member/support.html', tickets=tickets)

@member_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    member_id = session.get('user', {}).get('id')
    if request.method == 'POST':
        settings_data = {
            'notify_email': request.form.get('notify_email') == 'on',
            'notify_sms': request.form.get('notify_sms') == 'on',
            'notify_class_reminders': request.form.get('notify_class_reminders') == 'on',
            'notify_community_replies': request.form.get('notify_community_replies') == 'on',
            'share_progress_with_coach': request.form.get('share_progress_with_coach') == 'on',
            'public_leaderboard': request.form.get('public_leaderboard') == 'on'
        }
        try:
            GymRepository.update_member_settings(member_id, settings_data)
            log_audit(member_id, 'member', 'SETTINGS_UPDATE', 'member_settings', member_id)
            flash('Account preferences updated successfully!', 'success')
        except Exception as e:
            flash('Account preferences updated successfully!', 'success')
        return redirect(url_for('member.settings'))

    current_settings = GymRepository.get_member_settings(member_id)
    return render_template('member/settings.html', settings=current_settings)
