from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import Notification

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/notifications/unread-count")
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"unread": count})
