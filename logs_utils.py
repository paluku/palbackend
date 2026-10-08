from flask import request
from flask_login import current_user
from extensions import db
from models import ActivityLog


def log_action(action, details=None, user=None):
    """Enregistre une action."""
    try:
        user_id = None
        if user:
            user_id = user.id
        elif current_user and current_user.is_authenticated:
            user_id = current_user.id

        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details[:255] if details else None,
            ip=request.remote_addr if request else None,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"⚠️ Erreur log : {e}")