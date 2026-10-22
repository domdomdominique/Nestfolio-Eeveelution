import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from app.entity.db import db

csrf = CSRFProtect()

# Development-only key so the app works out of the box for the whole group.
# For a real deployment, set the ENCRYPTION_KEY environment variable to a key
# made with:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
DEV_ENCRYPTION_KEY = "1dCtVD-SSy_dupVpi3OPSN3pxR6kAqcWwtK4vMg-NPA="


def create_app(test_config=None):
    """Application factory: builds and configures the Flask app."""
    app = Flask(__name__, template_folder="boundary/templates")
    app.config.update(
        # Set SECRET_KEY in the environment for any real deployment; the fallback is for local dev only.
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",  # set to 1 behind HTTPS
        MAX_CONTENT_LENGTH=110 * 1024 * 1024,  # upper bound for photo uploads (20 x 5 MB + form data)
        SQLALCHEMY_DATABASE_URI="sqlite:///eeveelution.db",
        ENCRYPTION_KEY=os.environ.get("ENCRYPTION_KEY", DEV_ENCRYPTION_KEY),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    # Boundary layer: one blueprint per actor
    from app.boundary.auth_boundary import auth_bp
    from app.boundary.customer_boundary import customer_bp
    from app.boundary.admin_boundary import admin_bp
    from app.boundary.designer_boundary import designer_bp
    from app.boundary.platform_boundary import platform_bp

    from app.boundary import drop_stale_login
    app.before_request(drop_stale_login)

    for bp in (auth_bp, customer_bp, admin_bp, designer_bp, platform_bp):
        app.register_blueprint(bp)

    with app.app_context():
        db.create_all()

    return app
