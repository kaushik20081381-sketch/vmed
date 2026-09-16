import os
import secrets
import sys
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    # SECRET_KEY is resolved at instance level so it can fall back to a
    # random per-run key when the environment provides nothing.
    # `.get("X", default)` only falls back when the var is entirely unset --
    # an empty `SECRET_KEY=` line in .env, or an empty OS-level env var,
    # still returns "" and breaks CSRF, so blank is explicitly treated the
    # same as missing.
    _env_secret = os.environ.get("SECRET_KEY")
    if _env_secret:
        SECRET_KEY = _env_secret
    else:
        SECRET_KEY = secrets.token_hex(32)
        print(
            "[config.py] WARNING: no SECRET_KEY found in the environment/.env -- "
            "using a random, temporary key for this run. Sessions/CSRF tokens "
            "will be invalidated every restart. Set SECRET_KEY in your .env "
            "for real use.",
            file=sys.stderr,
        )

    # --- Database ---
    # Primary target per spec: MySQL via SQLAlchemy.
    #   mysql+pymysql://<user>:<password>@<host>:<port>/<db_name>
    # For quick local demoing without a MySQL server, DATABASE_URL can be
    # pointed at sqlite:///demo.db instead -- see README for both options.
    DB_USER = os.environ.get("DB_USER") or "root"
    DB_PASSWORD = os.environ.get("DB_PASSWORD") or "Merfiya7512"
    DB_HOST = os.environ.get("DB_HOST") or "localhost"
    DB_PORT = os.environ.get("DB_PORT") or "3306"
    DB_NAME = os.environ.get("DB_NAME") or "medtimeline_ai"

    DEFAULT_MYSQL_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or DEFAULT_MYSQL_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Uploads ---
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {"pdf", "txt", "csv", "png", "jpg", "jpeg"}

    # --- Session ---
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # --- AI Summary ---
    # If set, ai_summary.py will attempt to call the Anthropic API for a
    # richer narrative summary. If unset (or the call fails), the app
    # transparently falls back to the built-in rule-based summary engine,
    # so the demo always works offline.
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

    WTF_CSRF_ENABLED = True
