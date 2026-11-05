from flask import make_response

from app.control.view_registration_status_controller import ViewRegistrationStatusController

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.boundary import safe_next
from app.control.apply_designer_controller import ApplyDesignerController
from app.control.change_password_controller import ChangePasswordController
from app.control.reset_password_controller import ResetPasswordController
from app.control.login_controller import LoginController
from app.control.register_controller import RegisterController
from app.control.validate_session_controller import ValidateSessionController
from app.entity.user_account import UserAccount
from app.control.view_landing_page_controller import ViewLandingPageController

auth_bp = Blueprint("auth", __name__)

HOME_BY_ROLE = {
    "admin": "admin.home",
    "designer": "designer.home",
    "customer": "customer.home",
    "platform": "platform.home",
}


@auth_bp.route("/")
def index():
    """Boundary: LandingPage (public customer landing page)."""
    customer_id = session["user_id"] if session.get("role") == "customer" else None
    page = ViewLandingPageController().view(request.args.get("sort"), customer_id)
    return render_template("customer/landing.html", **page)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Boundary: LoginPage (C-02, and the login for every other actor; redirects by the account's own role)."""
    if request.method == "POST":
        controller = LoginController()
        account = controller.login(request.form["email"], request.form["password"])
        if account:
            session.clear()
            session.permanent = bool(request.form.get("remember"))
            session["user_id"] = account.id
            session["role"] = account.role
            session["name"] = account.name
            session["auth"] = ValidateSessionController().token_for(account)
            next_url = safe_next(request.args.get("next"))
            return redirect(next_url or url_for(HOME_BY_ROLE.get(account.role, "auth.index")))
        application = controller.unapproved_application(request.form.get("email"), request.form.get("password"))
        if application:
            # Not approved yet: show their status card instead of a bare error.
            session.clear()
            session["application_id"] = application.id
            return redirect(url_for("auth.registration_status"))
        message = controller.failure_message(
            request.form.get("email"),
            request.form.get("password"),
        )
        flash(message, "error")
    return render_template("auth/login.html", form=request.form)


# C-01 Create customer account.
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Boundary: RegisterPage (C-01 customer sign-up, account is active immediately)."""
    if request.method == "POST":
        f = request.form
        try:
            RegisterController().register(
                _full_name(f), f.get("email"), f.get("phone"),
                f.get("password"), f.get("confirm_password"),
            )
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash("Account created! Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", account_type="customer", form=request.form)


def _full_name(form):
    """The sign-up forms ask for first and last name; accounts store one name."""
    if form.get("name"):
        return form.get("name")
    return f"{form.get('first_name', '').strip()} {form.get('last_name', '').strip()}".strip()


# ID-15 Register as an interior designer (application goes to the User Admin).
@auth_bp.route("/register/designer", methods=["GET", "POST"])
def apply_designer():
    """Boundary: ApplyDesignerPage (application goes to the User Admin for approval)."""
    if request.method == "POST":
        f = request.form
        try:
            application = ApplyDesignerController().apply(
                _full_name(f), f.get("email"), f.get("phone"),
                f.get("password"), f.get("confirm_password"),
                f.get("company_name"), f.get("uen"), f.get("portfolio_url"),
                f.get("experience_years"), f.get("description"),
            )
        except ValueError as error:
            flash(str(error), "error")
        else:
            # They just proved who they are, so show their status without asking again.
            session["application_id"] = application.id
            flash("Your designer application was submitted successfully.", "success")
            return redirect(url_for("auth.registration_status"))
    return render_template("auth/register.html", account_type="designer", form=request.form)


# C-03, ID-02, PM-02, UA-02 Log out: ends the session and returns to the login page.
@auth_bp.route("/logout")
def logout():
    was_logged_in = "user_id" in session

    session.clear()

    if was_logged_in:
        flash("You have logged out successfully.", "success")

    return redirect(url_for("auth.login"))



# ID-16 View registration status (pending, approved or rejected designers).
@auth_bp.route("/registration-status")
def registration_status():
    # Only reached after applying or after a login attempt by an unapproved applicant.
    try:
        application = ViewRegistrationStatusController().view(session.get("application_id"))
    except LookupError:
        session.pop("application_id", None)
        return redirect(url_for("auth.login"))

    response = make_response(
        render_template(
            "auth/registration_status.html",
            application=application,
        )
    )

    response.headers["Cache-Control"] = "no-store"

    return response


@auth_bp.route("/account/password", methods=["GET", "POST"])
def change_password():
    """Boundary: ChangePasswordPage, forced after a User Admin reset (UA-16), open to every role."""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        f = request.form
        try:
            ChangePasswordController().change(session["user_id"], f.get("current_password"),
                                              f.get("new_password"), f.get("confirm_password"))
        except ValueError as error:
            flash(str(error), "error")
        else:
            session["auth"] = ValidateSessionController().token_for(UserAccount.get(session["user_id"]))
            flash("Password updated.", "success")
            return redirect(url_for(HOME_BY_ROLE.get(session.get("role"), "auth.index")))
    return render_template(
        "auth/change_password.html",
        forced=ResetPasswordController().must_change_password(session["user_id"]),
        home_endpoint=HOME_BY_ROLE.get(session.get("role"), "auth.index"),
    )
