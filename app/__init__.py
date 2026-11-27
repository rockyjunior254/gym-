import os
from flask import Flask, session, g
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='../static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'strakly-gym-production-secret-2026')
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Register Blueprints
    from app.routes.public import public_bp
    from app.routes.admin import admin_bp
    from app.routes.trainer import trainer_bp
    from app.routes.member import member_bp
    from app.routes.community import community_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(trainer_bp, url_prefix='/trainer')
    app.register_blueprint(member_bp, url_prefix='/member')
    app.register_blueprint(community_bp, url_prefix='/community')

    # Global Context Processors
    @app.context_processor
    def inject_global_data():
        from app.services.supabase_client import db_service
        from app.services.repository import GymRepository
        
        user = session.get('user')
        settings = GymRepository.get_setting('general', {
            'gym_name': 'Strakly Fitness Platform',
            'tagline': 'TRAIN HARD. STAY STRONG. OWN YOUR PROGRESS.',
            'phone': '+254 700 123 456',
            'email': 'info@strakly.com',
            'address': 'Facility Wing B, Nairobi'
        })
        
        unread_notifications = 0
        if user and db_service.is_configured:
            notifs = GymRepository.get_user_notifications(user.get('id', ''))
            unread_notifications = sum(1 for n in notifs if not n.get('is_read', False))

        return {
            'current_user': user,
            'gym_settings': settings,
            'is_supabase_configured': db_service.is_configured,
            'unread_notifications_count': unread_notifications
        }

    return app
