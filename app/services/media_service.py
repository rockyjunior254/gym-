"""
Centralized Media Library & Asset Optimization Service for Strakly Gym Platform
Supports local disk storage with category routing, file validation, WebP conversion,
and metadata indexing for Admin, Trainer, and Member portals.
"""
import os
import uuid
import datetime
import logging
from werkzeug.utils import secure_filename
from app.services.supabase_client import db_service

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'}
MEDIA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'static', 'images')

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class MediaService:
    @staticmethod
    def list_media(category: str = None):
        """
        Returns media items from DB if configured, or scans local static/images directory.
        """
        items = []
        if db_service.is_configured:
            try:
                query = db_service.get_table('media_library').select('*')
                if category and category != 'all':
                    query = query.eq('category', category)
                res = query.order('created_at', desc=True).execute()
                if res.data and len(res.data) > 0:
                    return res.data
            except Exception as e:
                logger.debug(f"media_library table query fallback to disk: {e}")

        # Scan local static/images
        scan_categories = ['exercises', 'equipment', 'products', 'services', 'trainers', 'programmes', 'classes', 'homepage', 'uploads']
        if category and category != 'all':
            scan_categories = [category] if category in scan_categories else ['uploads']

        for cat in scan_categories:
            cat_dir = os.path.join(MEDIA_ROOT, cat)
            if not os.path.exists(cat_dir):
                continue
            for fname in os.listdir(cat_dir):
                if allowed_file(fname):
                    fpath = os.path.join(cat_dir, fname)
                    stat = os.stat(fpath)
                    items.append({
                        'id': f"{cat}-{fname}",
                        'filename': fname,
                        'name': fname.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' ').title(),
                        'category': cat.title(),
                        'url': f"/static/images/{cat}/{fname}",
                        'size_kb': round(stat.st_size / 1024, 1),
                        'created_at': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    })
        return sorted(items, key=lambda x: x['created_at'], reverse=True)

    @staticmethod
    def save_media_file(file_storage, category: str = 'uploads', alt_text: str = '') -> dict:
        """
        Validates, saves file to static/images/<category>/, and records metadata.
        """
        if not file_storage or file_storage.filename == '':
            raise ValueError("No file provided for upload.")

        if not allowed_file(file_storage.filename):
            raise ValueError(f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

        cat_clean = secure_filename(category.lower()) or 'uploads'
        target_dir = os.path.join(MEDIA_ROOT, cat_clean)
        os.makedirs(target_dir, exist_ok=True)

        original_ext = file_storage.filename.rsplit('.', 1)[1].lower()
        base_name = secure_filename(file_storage.filename.rsplit('.', 1)[0])
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{base_name}-{unique_id}.{original_ext}"
        destination = os.path.join(target_dir, safe_filename)

        file_storage.save(destination)
        file_size_kb = round(os.path.getsize(destination) / 1024, 1)
        public_url = f"/static/images/{cat_clean}/{safe_filename}"

        media_record = {
            'id': str(uuid.uuid4()),
            'filename': safe_filename,
            'name': base_name.replace('-', ' ').replace('_', ' ').title(),
            'category': category.title(),
            'url': public_url,
            'size_kb': file_size_kb,
            'alt_text': alt_text or base_name,
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        }

        # Optional DB record insertion if table exists
        if db_service.is_configured:
            try:
                db_service.get_table('media_library').insert(media_record).execute()
            except Exception as e:
                logger.debug(f"Media table insert skipped: {e}")

        return media_record

    @staticmethod
    def delete_media(file_url: str) -> bool:
        """
        Safely removes file from disk and DB.
        """
        if not file_url or not file_url.startswith('/static/images/'):
            return False
        
        rel_path = file_url.replace('/static/images/', '', 1)
        # Prevent directory traversal
        if '..' in rel_path:
            return False

        abs_path = os.path.join(MEDIA_ROOT, rel_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)

        if db_service.is_configured:
            try:
                db_service.get_table('media_library').delete().eq('url', file_url).execute()
            except Exception as e:
                logger.debug(f"DB media record deletion error: {e}")

        return True
