import os
from flask import Flask, render_template
from config import Config
from extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.patient import patient_bp
    from routes.doctor import doctor_bp
    from routes.admin import admin_bp
    from routes.records import records_bp
    from routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from models import Notification
        unread = 0
        if current_user.is_authenticated:
            unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {"unread_notifications": unread}

    return app


app = create_app()

if __name__ == "__main__":
    print(f"[app.py] Using config.py from: {os.path.abspath('config.py')}")
    print(f"[app.py] SECRET_KEY is set: {bool(app.config.get('SECRET_KEY'))}")
    app.run(debug=True, host="0.0.0.0", port=5000)
