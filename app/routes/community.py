import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.auth_service import login_required
from app.services.repository import GymRepository
from app.services.supabase_client import db_service
from app.services.audit_service import log_audit

community_bp = Blueprint('community', __name__)

@community_bp.before_request
@login_required
def check_community_access():
    pass

@community_bp.route('/')
def index():
    posts = GymRepository.get_community_posts()
    groups = GymRepository.get_community_groups()
    return render_template('community/index.html', posts=posts, groups=groups)

@community_bp.route('/post', methods=['POST'])
def create_post():
    content = request.form.get('content', '').strip()
    image_url = request.form.get('image_url', '').strip() or None
    user = session.get('user', {})

    if not content:
        flash('Post content cannot be empty.', 'warning')
        return redirect(url_for('community.index'))

    if db_service.is_configured:
        try:
            db_service.get_table('community_posts').insert({
                'author_id': user.get('id'),
                'content': content,
                'image_url': image_url
            }).execute()

            log_audit(user.get('id'), user.get('role', 'user'), 'COMMUNITY_POST_CREATE', 'community_posts')
            flash('Your post has been shared with the community!', 'success')
        except Exception as e:
            flash(f"Error publishing post: {str(e)}", 'danger')
    else:
        log_audit(user.get('id'), user.get('role', 'user'), 'COMMUNITY_POST_CREATE', 'community_posts', details={'content': content})
        flash('Post shared in community feed (Config mode).', 'success')

    return redirect(url_for('community.index'))

@community_bp.route('/post/<post_id>/comment', methods=['POST'])
def add_comment(post_id):
    content = request.form.get('content', '').strip()
    user = session.get('user', {})

    if not content:
        flash('Comment cannot be empty.', 'warning')
        return redirect(url_for('community.index'))

    if db_service.is_configured:
        try:
            db_service.get_table('community_comments').insert({
                'post_id': post_id,
                'author_id': user.get('id'),
                'content': content
            }).execute()
            flash('Comment posted!', 'success')
        except Exception as e:
            flash(f"Error adding comment: {str(e)}", 'danger')
    else:
        flash('Comment posted (Config mode).', 'success')

    return redirect(url_for('community.index'))

@community_bp.route('/messages')
def messages():
    return render_template('community/messages.html')

@community_bp.route('/notifications')
def notifications():
    user_id = session.get('user', {}).get('id')
    notifs = GymRepository.get_user_notifications(user_id)
    return render_template('community/notifications.html', notifications=notifs)
