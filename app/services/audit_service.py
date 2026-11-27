import logging
from flask import request
from app.services.supabase_client import db_service

logger = logging.getLogger(__name__)

def log_audit(actor_id, actor_role, action_type, target_entity, target_id=None, details=None, reason=None):
    """
    Append-only audit logging service for all sensitive actions.
    Records actor, role, action, target entity, timestamp, IP address, and details.
    """
    if not db_service.is_configured:
        logger.info(f"[AUDIT LOG (Config Mode)] {actor_role} ({actor_id}) -> {action_type} on {target_entity}:{target_id} | Reason: {reason}")
        return None

    try:
        ip = request.remote_addr if request else '127.0.0.1'
        payload = {
            'actor_id': actor_id,
            'actor_role': actor_role,
            'action_type': action_type,
            'target_entity': target_entity,
            'target_id': str(target_id) if target_id else None,
            'details': details or {},
            'reason': reason,
            'ip_address': ip
        }
        res = db_service.get_table('audit_logs').insert(payload).execute()
        return res.data
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
        return None
