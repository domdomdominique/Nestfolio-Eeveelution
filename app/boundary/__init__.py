from functools import wraps

from flask import abort, redirect, request, session, url_for

from app.control.validate_session_controller import ValidateSessionController


def role_required(role):
    """Only let logged-in users with this role open the page."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                # Come back to this page after logging in
                return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
            if session.get("role") != role:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def safe_next(url):
    """Return url only if it is a path on this site (blocks open redirects)."""
    if url and url.startswith("/") and not url.startswith(("//", "/\\")):
        return url
    return None


def drop_stale_login():
    """Run before every request: forget a login that no longer matches an active account."""
    if request.endpoint == "static" or "user_id" not in session:
        return
    if not ValidateSessionController().is_valid(
            session.get("user_id"), session.get("role"), session.get("auth")):
        session.clear()
