import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL', '').strip()
        # Prefer secret key on server-side backend, or fallback to standard publishable key
        self.key = (os.getenv('SUPABASE_SECRET_KEY') or 
                    os.getenv('SUPABASE_KEY') or 
                    os.getenv('SUPABASE_PUBLISHABLE_KEY', '')).strip()
        # Fix accidental leading ssb_ typo if present
        if self.key.startswith('ssb_'):
            self.key = self.key[1:]
        self.client = None
        self._init_client()

    def _init_client(self):
        # Check if valid URL and key are provided
        if not self.url or not self.key or 'your-project-id' in self.url or 'your-supabase' in self.key:
            logger.info("Supabase credentials not configured. Operating in graceful configuration mode.")
            return

        try:
            from supabase import create_client
            self.client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Supabase client: {e}")
            self.client = None

    @property
    def is_configured(self):
        return self.client is not None

    def get_table(self, table_name: str):
        if not self.is_configured:
            return None
        return self.client.table(table_name)

# Global singleton service
db_service = SupabaseService()
