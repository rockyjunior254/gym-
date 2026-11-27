from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('public.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('public.login'))
            
            user_role = session.get('user', {}).get('role')
            if user_role not in allowed_roles:
                flash('You do not have permission to view that section.', 'danger')
                if user_role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user_role == 'trainer':
                    return redirect(url_for('trainer.dashboard'))
                else:
                    return redirect(url_for('member.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required('admin')
trainer_required = role_required('trainer')
member_required = role_required('member')
