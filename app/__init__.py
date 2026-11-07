import os
import secrets
import sqlite3
import time

from cryptography.fernet import Fernet
from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError
from flask_wtf.csrf import CSRFProtect

from app.entity.db import db


csrf = CSRFProtect()

# Throwaway keys for the automated tests only; real runs use _load_secret below.
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()
TEST_SECRET_KEY = "test-only-secret"


def _load_secret(app, name, make, database=None):
    """The secret from the environment, else from a git-ignored file in instance/ (made on first run).

    No secret is ever written in the source code, so a copy of the repository cannot forge a
    login or read the encrypted data. If `database` already exists but its key file is gone, a new
    key would make the saved data unreadable, so we stop instead of quietly making one.
    """
    if os.environ.get(name):
        return os.environ[name]
    os.makedirs(app.instance_path, exist_ok=True)
    path = os.path.join(app.instance_path, name.lower() + ".key")
    if not os.path.exists(path):
        if database and os.path.exists(database):
            raise RuntimeError(
                f"{os.path.basename(path)} is missing but {os.path.basename(database)} exists, so the "
                f"saved data could not be read. Put the key file back, or delete the database and run: python seed.py"
            )
        # Write the whole key to a temporary file, then link it into place in one step, so another
        # process starting at the same moment never reads half a key and only one key ever wins.
        temp = f"{path}.{os.getpid()}.tmp"
        with open(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
            handle.write(make())
        try:
            os.link(temp, path)
        except FileExistsError:
            pass  # another process made it first: use theirs
        finally:
            os.remove(temp)
    with open(path) as handle:
        return handle.read().strip()


@event.listens_for(Engine, "connect")
def _sqlite_for_several_workers(dbapi_connection, _record):
    """Several Gunicorn workers share one SQLite file: wait for a busy file instead of failing with
    "database is locked", and let readers work while another worker writes (WAL)."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA journal_mode=WAL")  # stays "memory" for an in-memory test database
        cursor.close()


def create_app(test_config=None):
    """Application factory: builds and configures the Flask app."""
    # Days, "today" and report periods follow Singapore time whatever the server's clock says
    # (cloud hosts run UTC). Set APP_TIMEZONE to change it. Windows has no tzset: the PC's own setting applies.
    os.environ["TZ"] = os.environ.get("APP_TIMEZONE", "Asia/Singapore")
    if hasattr(time, "tzset"):
        time.tzset()

    app = Flask(
        __name__,
        template_folder="boundary/templates",
    )

    testing = bool(test_config and test_config.get("TESTING"))

    app.config.update(
        SECRET_KEY=(
            TEST_SECRET_KEY if testing
            else _load_secret(app, "SECRET_KEY", lambda: secrets.token_urlsafe(48))
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=(
            os.environ.get("SESSION_COOKIE_SECURE") == "1"
        ),
        MAX_CONTENT_LENGTH=110 * 1024 * 1024,
        SQLALCHEMY_DATABASE_URI="sqlite:///eeveelution.db",
        ENCRYPTION_KEY=(
            TEST_ENCRYPTION_KEY if testing
            else _load_secret(app, "ENCRYPTION_KEY", lambda: Fernet.generate_key().decode(),
                              database=os.path.join(app.instance_path, "eeveelution.db"))
        ),
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)

    from app.entity.designer_company import DesignerCompany
    from app.entity.idp_photo import IDPPhoto
    from app.entity.idp_view import IDPView
    from app.entity import activity_report, announcement  # noqa: F401  (PM-08, UA-18)
    from app.entity import reply  # noqa: F401  (ID-21 replies)
    from app.entity import enquiry_attachment  # noqa: F401  (C-16 attachments)
    from app.entity.idp_category import IDPCategory
    from app.entity.user_profile import UserProfile

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault(
            "X-Content-Type-Options",
            "nosniff",
        )
        response.headers.setdefault(
            "X-Frame-Options",
            "DENY",
        )
        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )
        return response

    from app.boundary.auth_boundary import auth_bp
    from app.boundary.customer_boundary import customer_bp
    from app.boundary.admin_boundary import admin_bp
    from app.boundary.designer_boundary import designer_bp
    from app.boundary.platform_boundary import platform_bp

    from app.boundary import drop_stale_login, force_password_change

    app.before_request(drop_stale_login)
    app.before_request(force_password_change)

    for bp in (
        auth_bp,
        customer_bp,
        admin_bp,
        designer_bp,
        platform_bp,
    ):
        app.register_blueprint(bp)

    # Over-time charts (inline SVG) on the Reports, Statistics and Trends pages
    from app.boundary.charts import line_chart
    app.jinja_env.globals["line_chart"] = line_chart

    # Short times and initials for the Enquiries inbox
    from app.boundary import timefmt
    for name in ("ago", "clock", "day_label", "initials"):
        app.jinja_env.filters[name] = getattr(timefmt, name)

    @app.errorhandler(IntegrityError)
    def unique_race(error):
        """Two requests saved the same unique value (email, phone, ...) at once: say so instead of a 500 page.
        Any other integrity error is a real bug, so it still surfaces as one."""
        from urllib.parse import urlparse

        from flask import flash, redirect, request, url_for

        db.session.rollback()
        if "UNIQUE" not in str(error.orig).upper():
            raise error
        app.logger.warning("Two requests saved the same unique value: %s", error.orig)
        flash("That was just saved by someone else. Please check and try again.", "error")
        back = request.referrer
        return redirect(back if back and urlparse(back).netloc == request.host else url_for("auth.index"))

    # ID-21 notification badge: number of enquiry conversations with new messages
    @app.context_processor
    def enquiry_notifications():
        from flask import session

        from app.control.enquiry_notification_controller import EnquiryNotificationController

        if session.get("role") in ("designer", "customer") and session.get("user_id"):
            return {"unread_enquiries": EnquiryNotificationController().unread_count(session["user_id"])}
        return {"unread_enquiries": 0}

    with app.app_context():
        # Every worker runs this set-up when it starts. If another one got there first ("table already
        # exists", "duplicate column", a default row added twice), look again and carry on.
        for attempt in (1, 2, 3):
            try:
                db.create_all()
                enquiry_attachment.EnquiryAttachment.ensure_schema()
                from app.entity.report import Report
                Report.ensure_schema()
                from app.entity.announcement import Announcement
                Announcement.ensure_schema()
                IDPCategory.ensure_defaults()
                UserProfile.ensure_defaults()
                break
            except (OperationalError, IntegrityError):
                db.session.rollback()
                if attempt == 3:
                    raise
                time.sleep(0.3 * attempt)

    return app
