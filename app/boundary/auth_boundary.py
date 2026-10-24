import secrets
from hmac import compare_digest

from flask import abort, make_response

from app.control.view_registration_status_controller import ViewRegistrationStatusController

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.boundary import safe_next
from app.control.apply_designer_controller import ApplyDesignerController
from app.control.login_controller import LoginController
from app.control.register_controller import RegisterController
from app.control.validate_session_controller import ValidateSessionController
from app.control.view_landing_page_controller import ViewLandingPageController

auth_bp = Blueprint("auth", __name__)

HOME_BY_ROLE = {
    "admin": "admin.home",
    "designer": "designer.home",
    "customer": "customer.home",
    "platform": "platform.home",
}

# "Log in as" choices on the login page (C-02, ID-01, PM-01, UA-01)
LOGIN_ROLES = {
    "customer": "Customer",
    "designer": "Interior Designer",
    "platform": "Platform Management",
    "admin": "User Admin",
}

APPLICATION_MESSAGES = {
    "pending": "Your designer application is still being reviewed. "
               "You can log in once an admin approves it.",
    "rejected": "Your designer application was not approved. "
                "Please contact us or apply again.",
}


@auth_bp.route("/")
def index():
    """Boundary: LandingPage (public customer landing page)."""
    customer_id = session["user_id"] if session.get("role") == "customer" else None
    page = ViewLandingPageController().view(request.args.get("sort"), customer_id)
    return render_template("customer/landing.html", **page)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Boundary: LoginPage (C-02, and the login for every other actor)."""
    if request.method == "POST":
        controller = LoginController()
        role = request.form.get("role") if request.form.get("role") in LOGIN_ROLES else None
        account = controller.login(request.form["email"], request.form["password"], role)
        if account:
            session.clear()
            session.permanent = bool(request.form.get("remember"))
            session["user_id"] = account.id
            session["role"] = account.role
            session["name"] = account.name
            session["auth"] = ValidateSessionController().token_for(account)
            next_url = safe_next(request.args.get("next"))
            return redirect(next_url or url_for(HOME_BY_ROLE[account.role]))
        message = controller.failure_message(
            request.form.get("email"),
            request.form.get("password"),
            role,
        )
        flash(message, "error")
    return render_template("auth/login.html", roles=LOGIN_ROLES, form=request.form)


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


@auth_bp.route("/register/designer", methods=["GET", "POST"])
def apply_designer():
    """Boundary: ApplyDesignerPage (application goes to the User Admin for approval)."""
    if request.method == "POST":
        f = request.form
        try:
            ApplyDesignerController().apply(
                _full_name(f), f.get("email"), f.get("phone"),
                f.get("password"), f.get("confirm_password"),
                f.get("company_name"), f.get("uen"), f.get("portfolio_url"),
                f.get("experience_years"), f.get("description"),
            )
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash(
                "Your designer application was submitted successfully. "
                "Your registration status is Pending. "
                "You can log in after an administrator approves it.",
                "success",
            )

            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", account_type="designer", form=request.form)


@auth_bp.route("/logout")
def logout():
    was_designer = session.get("role") == "designer"
    was_logged_in = "user_id" in session

    session.clear()

    if was_logged_in:
        flash("You have logged out successfully.", "success")

    return redirect(
        url_for("auth.login" if was_designer else "auth.index")
    )



@auth_bp.route(
    "/registration-status",
    methods=["GET", "POST"],
)
def registration_status():
    controller = ViewRegistrationStatusController()

    if request.method == "POST":
        try:
            application = controller.authenticate(
                request.form.get("email"),
                request.form.get("password"),
            )

        except ValueError as error:
            session.pop("application_id", None)
            flash(str(error), "error")

        else:
            session["application_id"] = application.id

            return redirect(
                url_for("auth.registration_status")
            )

    application = None

    if session.get("application_id"):
        try:
            application = controller.view(
                session["application_id"]
            )

        except LookupError:
            session.pop("application_id", None)

    response = make_response(
        render_template(
            "auth/registration_status.html",
            application=application,
        )
    )

    response.headers["Cache-Control"] = "no-store"

    return response