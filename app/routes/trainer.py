import datetime
import io
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from app.services.auth_service import trainer_required
from app.services.repository import GymRepository
from app.services.supabase_client import db_service
from app.services.audit_service import log_audit

trainer_bp = Blueprint('trainer', __name__)

@trainer_bp.before_request
@trainer_required
def check_trainer_access():
    pass

# =========================================================================
# 1. COACH DASHBOARD
# =========================================================================
@trainer_bp.route('/dashboard')
def dashboard():
    trainer_id = session.get('user', {}).get('id')
    trainer_name = session.get('user', {}).get('full_name', 'Coach')
    
    kpis = GymRepository.get_trainer_dashboard_kpis(trainer_id)
    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)
    today_sessions = GymRepository.get_trainer_sessions(trainer_id, datetime.date.today().isoformat())
    upcoming_sessions = GymRepository.get_trainer_sessions(trainer_id)[:5]
    checkins = GymRepository.get_trainer_checkins(trainer_id, status_filter='pending')[:5]
    exercises = GymRepository.get_exercise_library()[:8]

    # Weekly coaching chart data
    chart_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    chart_activity = [3, 5, 4, 6, 7, 5, 2] # Fallback realistic distribution
    
    return render_template('trainer/dashboard.html',
                           trainer_name=trainer_name,
                           kpis=kpis,
                           members=assigned_members,
                           today_sessions=today_sessions,
                           upcoming_sessions=upcoming_sessions,
                           checkins=checkins,
                           exercises=exercises,
                           chart_labels=chart_labels,
                           chart_activity=chart_activity)

# =========================================================================
# 2. MY ATHLETES & ATHLETE DETAIL
# =========================================================================
@trainer_bp.route('/members')
def members():
    trainer_id = session.get('user', {}).get('id')
    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)
    return render_template('trainer/members.html', members=assigned_members)

@trainer_bp.route('/members/<member_id>')
def member_detail(member_id):
    trainer_id = session.get('user', {}).get('id')
    detail = GymRepository.get_assigned_athlete_detail(trainer_id, member_id)
    
    if not detail:
        flash("Athlete record not found or not assigned to your coaching roster.", "warning")
        return redirect(url_for('trainer.members'))
        
    return render_template('trainer/member_detail.html',
                           athlete=detail['profile'],
                           details=detail['details'],
                           plans=detail['plans'],
                           progress_logs=detail['progress_logs'],
                           sessions=detail['sessions'],
                           assessments=detail['assessments'],
                           checkins=detail['checkins'])

# =========================================================================
# 3. WORKOUT PLANNER
# =========================================================================
@trainer_bp.route('/plans', methods=['GET', 'POST'])
def plans():
    trainer_id = session.get('user', {}).get('id')

    if request.method == 'POST':
        member_id = request.form.get('member_id')
        title = request.form.get('title', '').strip()
        goal = request.form.get('goal', '')
        days_per_week = int(request.form.get('days_per_week', 3))
        notes = request.form.get('notes', '')

        if not title:
            flash("Plan title is required.", "warning")
            return redirect(url_for('trainer.plans'))

        if db_service.is_configured:
            try:
                res = db_service.get_table('workout_plans').insert({
                    'member_id': member_id,
                    'trainer_id': trainer_id,
                    'title': title,
                    'goal': goal,
                    'days_per_week': days_per_week,
                    'status': 'active',
                    'notes': notes
                }).execute()

                log_audit(trainer_id, 'trainer', 'WORKOUT_PLAN_CREATE', 'workout_plans', res.data[0]['id'] if res.data else None, {'title': title})
                flash(f"Workout Plan '{title}' published for athlete.", 'success')
            except Exception as e:
                flash(f"Error publishing workout plan: {str(e)}", 'danger')
        else:
            flash(f"Workout Plan '{title}' published (Config mode).", 'success')
        return redirect(url_for('trainer.plans'))

    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)
    plans_list = GymRepository.get_trainer_workout_plans(trainer_id)
    exercises = GymRepository.get_exercise_library()
    return render_template('trainer/plans.html', members=assigned_members, plans=plans_list, exercises=exercises)

@trainer_bp.route('/plans/edit/<plan_id>', methods=['POST'])
def edit_plan(plan_id):
    trainer_id = session.get('user', {}).get('id')
    title = request.form.get('title', '').strip()
    goal = request.form.get('goal', '')
    days_per_week = int(request.form.get('days_per_week', 3))
    status = request.form.get('status', 'active')
    notes = request.form.get('notes', '')

    if db_service.is_configured:
        try:
            db_service.get_table('workout_plans').update({
                'title': title,
                'goal': goal,
                'days_per_week': days_per_week,
                'status': status,
                'notes': notes,
                'updated_at': datetime.datetime.now().isoformat()
            }).eq('id', plan_id).eq('trainer_id', trainer_id).execute()

            log_audit(trainer_id, 'trainer', 'WORKOUT_PLAN_UPDATE', 'workout_plans', plan_id, {'title': title})
            flash(f"Workout Plan '{title}' updated successfully.", 'success')
        except Exception as e:
            flash(f"Error updating plan: {str(e)}", 'danger')
    else:
        flash(f"Workout Plan '{title}' updated (Config mode).", 'success')
    return redirect(url_for('trainer.plans'))

@trainer_bp.route('/plans/delete/<plan_id>', methods=['POST'])
def delete_plan(plan_id):
    trainer_id = session.get('user', {}).get('id')
    if db_service.is_configured:
        try:
            db_service.get_table('workout_plans').delete().eq('id', plan_id).eq('trainer_id', trainer_id).execute()
            log_audit(trainer_id, 'trainer', 'WORKOUT_PLAN_DELETE', 'workout_plans', plan_id)
            flash("Workout plan removed.", 'info')
        except Exception as e:
            flash(f"Error deleting plan: {str(e)}", 'danger')
    return redirect(url_for('trainer.plans'))

# =========================================================================
# 4. MOVEMENT LIBRARY
# =========================================================================
@trainer_bp.route('/library')
def library():
    exercises = GymRepository.get_exercise_library()
    target_muscle = request.args.get('muscle', '')
    difficulty = request.args.get('difficulty', '')
    
    if target_muscle:
        exercises = [e for e in exercises if (e.get('target_muscle_group') or '').lower() == target_muscle.lower()]
    if difficulty:
        exercises = [e for e in exercises if (e.get('difficulty') or '').lower() == difficulty.lower()]
        
    return render_template('trainer/library.html', exercises=exercises, selected_muscle=target_muscle, selected_diff=difficulty)

# =========================================================================
# 5. MY SCHEDULE & AVAILABILITY
# =========================================================================
@trainer_bp.route('/schedule')
def schedule():
    trainer_id = session.get('user', {}).get('id')
    sessions = GymRepository.get_trainer_sessions(trainer_id)
    availability = GymRepository.get_trainer_availability(trainer_id)
    upcoming_classes = GymRepository.get_all_classes()
    # Filter classes assigned to this trainer
    trainer_classes = [c for c in upcoming_classes if c.get('trainer_id') == trainer_id]
    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)

    return render_template('trainer/schedule.html',
                           sessions=sessions,
                           availability=availability,
                           classes=trainer_classes,
                           members=assigned_members)

@trainer_bp.route('/schedule/availability', methods=['POST'])
def update_availability():
    trainer_id = session.get('user', {}).get('id')
    day_of_week = request.form.get('day_of_week', '').lower()
    start_time = request.form.get('start_time', '06:00')
    end_time = request.form.get('end_time', '20:00')
    is_available = (request.form.get('is_available') == 'on')
    notes = request.form.get('notes', '')

    success = GymRepository.update_trainer_availability(trainer_id, day_of_week, start_time, end_time, is_available, notes)
    if success:
        log_audit(trainer_id, 'trainer', 'TRAINER_AVAILABILITY_UPDATE', 'trainer_availability', None, {'day': day_of_week})
        flash(f"Availability for {day_of_week.capitalize()} updated.", 'success')
    else:
        flash("Could not update availability schedule.", 'danger')
    return redirect(url_for('trainer.schedule'))

# =========================================================================
# 6. TRAINING SESSIONS
# =========================================================================
@trainer_bp.route('/sessions', methods=['GET', 'POST'])
def sessions():
    trainer_id = session.get('user', {}).get('id')

    if request.method == 'POST':
        member_id = request.form.get('member_id')
        session_date = request.form.get('session_date')
        start_time = request.form.get('start_time')
        duration_minutes = int(request.form.get('duration_minutes', 60))
        focus_area = request.form.get('focus_area', 'Strength & Hypertrophy')
        notes = request.form.get('notes', '')

        res = GymRepository.create_trainer_session(trainer_id, member_id, session_date, start_time, duration_minutes, focus_area, notes)
        if res.get('success'):
            log_audit(trainer_id, 'trainer', 'TRAINING_SESSION_SCHEDULE', 'pt_sessions', None, {'date': session_date})
            flash(f"Training session scheduled for {session_date} at {start_time}.", 'success')
        else:
            flash(res.get('error', 'Failed to schedule session.'), 'danger')
        return redirect(url_for('trainer.sessions'))

    sessions_list = GymRepository.get_trainer_sessions(trainer_id)
    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)
    return render_template('trainer/sessions.html', sessions=sessions_list, members=assigned_members)

@trainer_bp.route('/sessions/<session_id>/complete', methods=['POST'])
def complete_session(session_id):
    trainer_id = session.get('user', {}).get('id')
    notes = request.form.get('notes', '')
    success = GymRepository.update_session_status(session_id, trainer_id, 'completed', notes)
    if success:
        log_audit(trainer_id, 'trainer', 'TRAINING_SESSION_COMPLETE', 'pt_sessions', session_id)
        flash("Session marked completed.", 'success')
    else:
        flash("Could not complete session.", 'danger')
    return redirect(url_for('trainer.sessions'))

@trainer_bp.route('/sessions/<session_id>/cancel', methods=['POST'])
def cancel_session(session_id):
    trainer_id = session.get('user', {}).get('id')
    reason = request.form.get('reason', 'Coach reschedule')
    success = GymRepository.update_session_status(session_id, trainer_id, 'cancelled', f"Cancelled: {reason}")
    if success:
        log_audit(trainer_id, 'trainer', 'TRAINING_SESSION_CANCEL', 'pt_sessions', session_id, {'reason': reason})
        flash("Session cancelled.", 'info')
    else:
        flash("Could not cancel session.", 'danger')
    return redirect(url_for('trainer.sessions'))

# =========================================================================
# 7. ATHLETE PROGRESS
# =========================================================================
@trainer_bp.route('/progress', methods=['GET', 'POST'])
def progress():
    trainer_id = session.get('user', {}).get('id')

    if request.method == 'POST':
        member_id = request.form.get('member_id')
        weight = float(request.form.get('weight_kg', 0)) if request.form.get('weight_kg') else None
        body_fat = float(request.form.get('body_fat_pct', 0)) if request.form.get('body_fat_pct') else None
        chest = float(request.form.get('chest_cm', 0)) if request.form.get('chest_cm') else None
        waist = float(request.form.get('waist_cm', 0)) if request.form.get('waist_cm') else None
        arms = float(request.form.get('arms_cm', 0)) if request.form.get('arms_cm') else None
        notes = request.form.get('notes', '')

        if db_service.is_configured:
            try:
                db_service.get_table('fitness_progress').insert({
                    'member_id': member_id,
                    'recorded_by': trainer_id,
                    'weight_kg': weight,
                    'body_fat_pct': body_fat,
                    'chest_cm': chest,
                    'waist_cm': waist,
                    'arms_cm': arms,
                    'notes': notes
                }).execute()

                log_audit(trainer_id, 'trainer', 'PROGRESS_MEASUREMENT_RECORD', 'fitness_progress', member_id, {'weight': weight})
                flash("Athlete progress measurements recorded successfully.", 'success')
            except Exception as e:
                flash(f"Error recording progress: {str(e)}", 'danger')
        else:
            flash("Athlete progress measurements recorded (Config mode).", 'success')
        return redirect(url_for('trainer.progress'))

    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)
    selected_member_id = request.args.get('member_id')
    progress_records = []
    selected_member = None

    if assigned_members:
        selected_member_id = selected_member_id or assigned_members[0]['id']
        selected_member = next((m for m in assigned_members if str(m['id']) == str(selected_member_id)), assigned_members[0])
        if db_service.is_configured and selected_member:
            try:
                res = db_service.get_table('fitness_progress').select('*').eq('member_id', selected_member['id']).order('record_date', desc=True).execute()
                progress_records = res.data or []
            except Exception:
                progress_records = []

    return render_template('trainer/progress.html',
                           members=assigned_members,
                           selected_member=selected_member,
                           progress_records=progress_records)

# =========================================================================
# 8. FEEDBACK & CHECK-INS
# =========================================================================
@trainer_bp.route('/feedback')
def feedback():
    trainer_id = session.get('user', {}).get('id')
    status_filter = request.args.get('status', 'all')
    checkins = GymRepository.get_trainer_checkins(trainer_id, None if status_filter == 'all' else status_filter)
    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)
    return render_template('trainer/feedback.html', checkins=checkins, status_filter=status_filter, members=assigned_members)

@trainer_bp.route('/feedback/<checkin_id>/reply', methods=['POST'])
def reply_feedback(checkin_id):
    trainer_id = session.get('user', {}).get('id')
    reply_text = request.form.get('feedback', '').strip()
    
    if not reply_text:
        flash("Feedback cannot be blank.", "warning")
        return redirect(url_for('trainer.feedback'))
        
    success = GymRepository.submit_checkin_feedback(checkin_id, trainer_id, reply_text)
    if success:
        log_audit(trainer_id, 'trainer', 'CHECKIN_FEEDBACK_SUBMIT', 'athlete_checkins', checkin_id)
        flash("Coaching feedback submitted directly to athlete.", "success")
    else:
        flash("Could not submit feedback.", "danger")
    return redirect(url_for('trainer.feedback'))

# =========================================================================
# 9. ASSESSMENTS & EVALUATIONS
# =========================================================================
@trainer_bp.route('/assessments', methods=['GET', 'POST'])
def assessments():
    trainer_id = session.get('user', {}).get('id')

    if request.method == 'POST':
        member_id = request.form.get('member_id')
        data = {
            'assessment_date': request.form.get('assessment_date'),
            'fitness_objectives': request.form.get('fitness_objectives', ''),
            'general_observations': request.form.get('general_observations', ''),
            'strength_observations': request.form.get('strength_observations', ''),
            'endurance_observations': request.form.get('endurance_observations', ''),
            'mobility_observations': request.form.get('mobility_observations', ''),
            'recommendations': request.form.get('recommendations', ''),
            'next_review_date': request.form.get('next_review_date')
        }
        success = GymRepository.create_fitness_assessment(trainer_id, member_id, data)
        if success:
            log_audit(trainer_id, 'trainer', 'FITNESS_ASSESSMENT_CREATE', 'fitness_assessments', member_id)
            flash("Fitness evaluation record filed successfully.", "success")
        else:
            flash("Could not save assessment.", "danger")
        return redirect(url_for('trainer.assessments'))

    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)
    assessments_list = GymRepository.get_trainer_assessments(trainer_id)
    return render_template('trainer/assessments.html', members=assigned_members, assessments=assessments_list)

# =========================================================================
# 10. MY REPORTS
# =========================================================================
@trainer_bp.route('/reports')
def reports():
    trainer_id = session.get('user', {}).get('id')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    export_csv = request.args.get('export') == 'csv'

    sessions = GymRepository.get_trainer_sessions(trainer_id)
    assigned_members = GymRepository.get_trainer_assigned_members(trainer_id)
    plans = GymRepository.get_trainer_workout_plans(trainer_id)

    if export_csv:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Session ID', 'Athlete Name', 'Date', 'Time', 'Focus Area', 'Status'])
        for s in sessions:
            p_name = s.get('profiles', {}).get('full_name') if s.get('profiles') else 'Athlete'
            writer.writerow([s.get('id'), p_name, s.get('session_date'), s.get('start_time'), s.get('focus_area'), s.get('status')])

        resp = make_response(output.getvalue())
        resp.headers['Content-Disposition'] = 'attachment; filename=strakly_coaching_report.csv'
        resp.headers['Content-type'] = 'text/csv'
        return resp

    return render_template('trainer/reports.html',
                           sessions=sessions,
                           members=assigned_members,
                           plans=plans,
                           start_date=start_date,
                           end_date=end_date)

# =========================================================================
# 11. COMMUNITY HUB
# =========================================================================
@trainer_bp.route('/community')
def community():
    posts = GymRepository.get_community_posts(include_hidden=False)
    groups = GymRepository.get_community_groups()
    return render_template('trainer/community.html', posts=posts, groups=groups)

# =========================================================================
# 12. ANNOUNCEMENTS & NOTIFICATIONS
# =========================================================================
@trainer_bp.route('/notifications')
def notifications():
    trainer_id = session.get('user', {}).get('id')
    notifications_list = GymRepository.get_user_notifications(trainer_id)
    announcements = GymRepository.get_all_announcements()
    return render_template('trainer/notifications.html', notifications=notifications_list, announcements=announcements)

@trainer_bp.route('/notifications/read', methods=['POST'])
def mark_notifications_read():
    trainer_id = session.get('user', {}).get('id')
    GymRepository.mark_notifications_read(trainer_id)
    flash("Notifications marked read.", "info")
    return redirect(url_for('trainer.notifications'))

# =========================================================================
# 13. MY COACH PROFILE & APPROVAL SUBMISSION
# =========================================================================
@trainer_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    trainer_id = session.get('user', {}).get('id')

    if request.method == 'POST':
        action = request.form.get('action', 'save')
        submit_for_approval = (action == 'submit_approval')

        profile_data = {
            'full_name': request.form.get('full_name', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'bio': request.form.get('bio', '').strip(),
            'specialisations': request.form.get('specialisations', '').strip(),
            'qualifications': request.form.get('qualifications', '').strip(),
            'certifications': request.form.get('certifications', '').strip(),
            'coaching_philosophy': request.form.get('coaching_philosophy', '').strip(),
            'experience_years': request.form.get('experience_years', 0)
        }

        success = GymRepository.update_trainer_public_profile(trainer_id, profile_data, submit_for_approval=submit_for_approval)
        if success:
            log_audit(trainer_id, 'trainer', 'COACH_PROFILE_UPDATE', 'trainer_details', trainer_id, {'submit': submit_for_approval})
            if submit_for_approval:
                flash("Coach profile submitted for Admin approval. It will appear on the public website once approved.", "success")
            else:
                flash("Profile draft saved.", "info")
        else:
            flash("Could not update profile.", "danger")
        return redirect(url_for('trainer.profile'))

    coach_profile = GymRepository.get_trainer_profile_detail(trainer_id)
    return render_template('trainer/profile.html', coach=coach_profile)

# =========================================================================
# 14. SPECIALISED COACHING PROGRAMMES (PART 5)
# =========================================================================
@trainer_bp.route('/programmes', methods=['GET', 'POST'])
def programmes():
    trainer_id = session.get('user', {}).get('id')

    if request.method == 'POST':
        data = {
            'name': request.form.get('name', '').strip(),
            'description': request.form.get('description', '').strip(),
            'objective': request.form.get('objective', '').strip(),
            'duration_weeks': request.form.get('duration_weeks', 6),
            'sessions_count': request.form.get('sessions_count', 18),
            'target_audience': request.form.get('target_audience', 'All Athletes').strip(),
            'category': request.form.get('category', 'Strength & Conditioning').strip(),
            'proposed_price': request.form.get('proposed_price', 0)
        }
        if not data['name']:
            flash("Programme name is required.", "warning")
            return redirect(url_for('trainer.programmes'))

        success = GymRepository.create_trainer_programme(trainer_id, data)
        if success:
            log_audit(trainer_id, 'trainer', 'PROGRAMME_PROPOSE', 'trainer_programmes', None, {'name': data['name']})
            flash(f"Programme '{data['name']}' submitted for Admin review. It will appear publicly upon approval.", "success")
        else:
            flash("Could not submit programme proposal.", "danger")
        return redirect(url_for('trainer.programmes'))

    programmes_list = GymRepository.get_trainer_programmes(trainer_id)
    services = GymRepository.get_published_services()
    return render_template('trainer/programmes.html', programmes=programmes_list, services=services)

@trainer_bp.route('/programmes/edit/<programme_id>', methods=['POST'])
def edit_programme(programme_id):
    trainer_id = session.get('user', {}).get('id')
    data = {
        'name': request.form.get('name', '').strip(),
        'description': request.form.get('description', '').strip(),
        'objective': request.form.get('objective', '').strip(),
        'duration_weeks': request.form.get('duration_weeks', 6),
        'sessions_count': request.form.get('sessions_count', 18),
        'target_audience': request.form.get('target_audience', 'All Athletes').strip(),
        'category': request.form.get('category', 'Strength & Conditioning').strip(),
        'proposed_price': request.form.get('proposed_price', 0)
    }
    success = GymRepository.update_trainer_programme(programme_id, trainer_id, data)
    if success:
        log_audit(trainer_id, 'trainer', 'PROGRAMME_UPDATE', 'trainer_programmes', programme_id)
        flash("Programme updated and re-submitted for Admin approval.", "success")
    else:
        flash("Could not update programme.", "danger")
    return redirect(url_for('trainer.programmes'))

@trainer_bp.route('/programmes/delete/<programme_id>', methods=['POST'])
def delete_programme(programme_id):
    trainer_id = session.get('user', {}).get('id')
    success = GymRepository.delete_trainer_programme(programme_id, trainer_id)
    if success:
        log_audit(trainer_id, 'trainer', 'PROGRAMME_DELETE', 'trainer_programmes', programme_id)
        flash("Programme proposal removed.", "info")
    else:
        flash("Could not delete programme.", "danger")
    return redirect(url_for('trainer.programmes'))

# =========================================================================
# 15. SETTINGS
# =========================================================================
@trainer_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    trainer_id = session.get('user', {}).get('id')

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        if db_service.is_configured:
            try:
                db_service.get_table('profiles').update({'full_name': full_name, 'phone': phone}).eq('id', trainer_id).execute()
                session['user']['full_name'] = full_name
                flash("Account details saved.", "success")
            except Exception as e:
                flash(f"Error saving settings: {e}", "danger")
        else:
            session['user']['full_name'] = full_name
            flash("Account details saved (Config mode).", "success")
        return redirect(url_for('trainer.settings'))

    user = session.get('user', {})
    return render_template('trainer/settings.html', user=user)

@trainer_bp.route('/change-password', methods=['POST'])
def change_password():
    trainer = session.get('user', {})
    trainer_id = trainer.get('id')
    email = trainer.get('email')

    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not current_password or not new_password or not confirm_password:
        flash('All password fields are required.', 'danger')
        return redirect(url_for('trainer.settings'))

    if new_password != confirm_password:
        flash('New password and confirmation do not match.', 'danger')
        return redirect(url_for('trainer.settings'))

    try:
        GymRepository.change_user_password(trainer_id, email, current_password, new_password)
        log_audit(trainer_id, 'trainer', 'PASSWORD_CHANGE_SUCCESS', 'auth.users', trainer_id)
        flash('Your coach account password has been updated securely.', 'success')
    except ValueError as val_err:
        flash(str(val_err), 'danger')
    except Exception as e:
        flash(f"Unable to update password: {str(e)}", 'danger')

    return redirect(url_for('trainer.settings'))
