from flask import Blueprint, render_template
from flask_login import current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html", logged_in_role=current_user.role)
    return render_template("index.html", logged_in_role=None)
