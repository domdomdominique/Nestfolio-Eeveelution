from functools import wraps

from flask import abort, redirect, request, session, url_for

from app.control.reset_password_controller import ResetPasswordController
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


def force_password_change():
    """Run before every request: after a User Admin reset (UA-16) the user must pick a new password first."""
    if request.endpoint in (None, "static", "auth.change_password", "auth.logout") or "user_id" not in session:
        return
    if ResetPasswordController().must_change_password(session["user_id"]):
        return redirect(url_for("auth.change_password"))


def send_attachment(user_id, attachment_id):
    """Send an enquiry attachment to its customer or designer (C-16, ID-21), or 404.

    Photos open in the browser; PDFs are downloaded. The response may not run
    scripts or be framed, so a crafted upload cannot act as a page on this site.
    """
    from io import BytesIO

    from flask import abort, send_file

    from app.control.view_enquiry_attachment_controller import ViewEnquiryAttachmentController

    try:
        attachment = ViewEnquiryAttachmentController().view(user_id, attachment_id)
    except LookupError:
        abort(404)
    response = send_file(BytesIO(attachment.data), mimetype=attachment.content_type,
                         download_name=attachment.filename, as_attachment=not attachment.is_image,
                         max_age=0)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; sandbox"
    return response
