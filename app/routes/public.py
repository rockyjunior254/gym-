from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.services.repository import GymRepository
from app.services.supabase_client import db_service
from app.services.audit_service import log_audit
from app.services.cache import cache

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
@cache.cached(timeout=300)
def index():
    services = GymRepository.get_published_services()
    plans = GymRepository.get_active_plans()
    trainers = GymRepository.get_published_trainers()
    classes = GymRepository.get_upcoming_classes()
    stats = GymRepository.get_public_stats()
    programmes = GymRepository.get_published_trainer_programmes()
    testimonials = GymRepository.get_public_testimonials()
    
    return render_template('public/index.html',
                           services=services,
                           plans=plans,
                           trainers=trainers,
                           classes=classes,
                           stats=stats,
                           programmes=programmes,
                           testimonials=testimonials)

@public_bp.route('/about')
@cache.cached(timeout=600)
def about():
    equipment = GymRepository.get_all_equipment()
    return render_template('public/about.html', equipment=equipment)

@public_bp.route('/programmes')
@cache.cached(timeout=600)
def programmes():
    services = GymRepository.get_published_services()
    programmes = GymRepository.get_published_trainer_programmes()
    return render_template('public/programmes.html', services=services, programmes=programmes)

@public_bp.route('/classes')
@cache.cached(timeout=300)
def classes():
    upcoming_classes = GymRepository.get_upcoming_classes()
    return render_template('public/classes.html', classes=upcoming_classes)

@public_bp.route('/trainers')
@cache.cached(timeout=600)
def trainers():
    all_trainers = GymRepository.get_published_trainers()
    return render_template('public/trainers.html', trainers=all_trainers)

@public_bp.route('/trainers/<trainer_id>')
def trainer_detail(trainer_id):
    trainer = GymRepository.get_trainer_profile_detail(trainer_id)
    if not trainer or not trainer.get('is_published', True):
        flash("Trainer profile is not publicly available.", "warning")
        return redirect(url_for('public.trainers'))
    return render_template('public/trainer_detail.html', trainer=trainer)

@public_bp.route('/memberships')
def memberships():
    plans = GymRepository.get_active_plans()
    return render_template('public/memberships.html', plans=plans)

@public_bp.route('/gallery')
def gallery():
    return render_template('public/gallery.html')

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', 'General Inquiry').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not message:
            flash("Please complete all required fields.", "warning")
            return render_template('public/contact.html')

        # Log inquiry into audit or support
        log_audit(None, 'public', 'CONTACT_INQUIRY', 'public_contact', None, {'name': name, 'email': email, 'subject': subject})
        flash("Thank you for reaching out! A facility representative will contact you shortly.", "success")
        return redirect(url_for('public.contact'))

    return render_template('public/contact.html')

@public_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('public/login.html')

        # Authentication against Supabase or demo administrative flow
        if db_service.is_configured:
            try:
                res = db_service.client.auth.sign_in_with_password({'email': email, 'password': password})
                user_id = res.user.id
                # Get profile
                prof_res = db_service.get_table('profiles').select('*').eq('id', user_id).execute()
                if prof_res.data:
                    profile = prof_res.data[0]
                    session['user'] = {
                        'id': profile['id'],
                        'email': profile['email'],
                        'full_name': profile['full_name'],
                        'role': profile['role'],
                        'avatar_url': profile.get('avatar_url')
                    }
                    log_audit(profile['id'], profile['role'], 'LOGIN_SUCCESS', 'auth', profile['id'])
                    flash(f"Welcome back, {profile['full_name']}!", 'success')
                    if profile['role'] == 'admin':
                        return redirect(url_for('admin.dashboard'))
                    elif profile['role'] == 'trainer':
                        return redirect(url_for('trainer.dashboard'))
                    else:
                        return redirect(url_for('member.dashboard'))
                else:
                    flash('User profile record not found. Please contact administration.', 'danger')
            except Exception as e:
                flash(f"Authentication failed: {str(e)}", 'danger')
        else:
            # Supabase pending configuration helper mode: allow signing into demo roles for evaluation
            # as documented in Part 1.3 & 19.5
            role_hint = request.form.get('role_hint', 'member')
            name_map = {
                'admin': 'Strakly Administrator',
                'trainer': 'Coach James Scott',
                'member': 'Oliver Bennett'
            }
            session['user'] = {
                'id': f"demo-{role_hint}-id",
                'email': email,
                'full_name': name_map.get(role_hint, 'Gym User'),
                'role': role_hint,
                'avatar_url': f"/static/images/trainers/trainer-1.jpg" if role_hint == 'trainer' else '/static/images/placeholders/avatar-default.svg'
            }
            log_audit(session['user']['id'], role_hint, 'LOGIN_EVALUATION', 'auth', session['user']['id'])
            flash(f"Logged into {role_hint.capitalize()} Portal (Evaluation Mode).", 'info')
            if role_hint == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role_hint == 'trainer':
                return redirect(url_for('trainer.dashboard'))
            else:
                return redirect(url_for('member.dashboard'))

    return render_template('public/login.html')

@public_bp.route('/register', methods=['GET', 'POST'])
def register():
    plans = GymRepository.get_active_plans()
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        plan_id = request.form.get('plan_id', '')

        if not full_name or not email or not password:
            flash('Please fill in all required fields.', 'warning')
            return render_template('public/register.html', plans=plans)

        if db_service.is_configured:
            try:
                auth_res = db_service.client.auth.sign_up({'email': email, 'password': password})
                user_id = auth_res.user.id
                # Create profile strictly as member
                db_service.get_table('profiles').insert({
                    'id': user_id,
                    'email': email,
                    'full_name': full_name,
                    'phone': phone,
                    'role': 'member'
                }).execute()

                # Generate member number
                import random
                member_num = f"STK-M-{random.randint(10000, 99999)}"
                db_service.get_table('member_details').insert({
                    'id': user_id,
                    'member_number': member_num
                }).execute()

                # Create pending subscription if plan selected
                if plan_id:
                    db_service.get_table('member_subscriptions').insert({
                        'member_id': user_id,
                        'plan_id': plan_id,
                        'status': 'pending',
                        'notes': 'Online registration awaiting cash payment verification'
                    }).execute()

                log_audit(user_id, 'member', 'MEMBER_REGISTER', 'profiles', user_id)
                flash('Account created successfully! Please present your cash payment at the gym front-desk to activate your membership.', 'success')
                return redirect(url_for('public.login'))
            except Exception as e:
                flash(f"Registration error: {str(e)}", 'danger')
        else:
            flash('Registration submitted! When Supabase is configured, member records persist directly. You can test login with any role selector below.', 'info')
            return redirect(url_for('public.login'))

    return render_template('public/register.html', plans=plans)

@public_bp.route('/logout')
def logout():
    user = session.pop('user', None)
    if user:
        log_audit(user.get('id'), user.get('role', 'user'), 'LOGOUT', 'auth', user.get('id'))
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('public.index'))
