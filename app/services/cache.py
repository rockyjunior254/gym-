"""
Centralized Caching Engine for Strakly Gym Management System
Using Flask-Caching with safe cache invalidation on mutations.
CRITICAL SECURITY: Never caches user-specific private records, sessions, passwords, or payments.
"""
import logging
from flask_caching import Cache

logger = logging.getLogger(__name__)

cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes default
    'CACHE_THRESHOLD': 1000
})

def init_cache(app):
    cache.init_app(app)
    logger.info("Strakly Flask-Caching initialized (SimpleCache).")

def invalidate_catalogues():
    """
    Invalidate shared public/catalogue caches when an admin adds/edits/archives:
    - Products
    - Services
    - Membership Plans
    - Exercise Movement Library
    - Equipment Directory
    - Public Trainers/Programmes
    """
    try:
        keys_to_clear = [
            'view//',
            'view//programmes',
            'view//classes',
            'view//trainers',
            'view//memberships',
            'view//about',
            'store_products_all',
            'exercise_library_all',
            'membership_plans_all',
            'facility_services_all',
            'gym_equipment_all',
            'general_settings'
        ]
        for key in keys_to_clear:
            cache.delete(key)
        logger.info("Cleared catalogue cache keys successfully.")
    except Exception as e:
        logger.warning(f"Error invalidating cache: {e}")
