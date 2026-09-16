from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from extensions import db
from models import Notification


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login_select"))
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def verified_doctor_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "doctor":
            return redirect(url_for("auth.login_select"))
        if not current_user.doctor_profile or not current_user.doctor_profile.is_verified:
            flash("Your doctor account is not yet verified. Access to patient records is restricted.", "warning")
            return redirect(url_for("doctor.dashboard"))
        return fn(*args, **kwargs)
    return wrapped


def notify(user_id, message, category="info", link=None):
    n = Notification(user_id=user_id, message=message, category=category, link=link)
    db.session.add(n)
    db.session.commit()
    return n


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions
