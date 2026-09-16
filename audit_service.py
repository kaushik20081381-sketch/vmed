from flask_login import current_user
from extensions import db
from models import AuditLog


def log_action(action, target_patient_id=None, details=None, commit=True):
    """Record an audit trail entry. Never raises -- auditing should never break a request."""
    try:
        actor_id = current_user.id if current_user and current_user.is_authenticated else None
        entry = AuditLog(
            actor_user_id=actor_id,
            action=action,
            target_patient_id=target_patient_id,
            details=details,
        )
        db.session.add(entry)
        if commit:
            db.session.commit()
    except Exception:
        db.session.rollback()
