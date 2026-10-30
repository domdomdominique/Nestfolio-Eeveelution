from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app.boundary import role_required
from app.control.paginate import paginate
from app.control.create_user_account_controller import CreateUserAccountController
from app.control.create_user_profile_controller import CreateUserProfileController
from app.control.reactivate_user_account_controller import ReactivateUserAccountController
from app.control.reset_password_controller import ResetPasswordController
from app.control.review_designer_application_controller import ReviewDesignerApplicationController
from app.control.review_reports_controller import ReviewReportsController
from app.control.search_user_account_controller import SearchUserAccountController
from app.control.search_user_profile_controller import SearchUserProfileController
from app.control.send_announcement_controller import SendAnnouncementController
from app.control.suspend_user_account_controller import SuspendUserAccountController
from app.control.suspend_user_profile_controller import SuspendUserProfileController
from app.control.update_user_account_controller import UpdateUserAccountController
from app.control.update_user_profile_controller import UpdateUserProfileController
from app.control.view_user_account_controller import ViewUserAccountController
from app.control.view_user_profile_controller import ViewUserProfileController
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.after_request
def no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@admin_bp.route("/")
@role_required("admin")
def home():
    pending = ReviewDesignerApplicationController().pending_count()
    return render_template("admin/home.html", nav="dashboard", pending=pending,
                           open_reports=ReviewReportsController().open_count(),
                           accounts=UserAccount.query.count(),
                           suspended=UserAccount.query.filter_by(is_suspended=True).count(),
                           announcements=SendAnnouncementController().latest(3))


# --- User accounts (UA-03 to UA-07, UA-13, UA-16) ---------------------------------

@admin_bp.route("/accounts")
@role_required("admin")
def accounts():
    """Boundary: UserAccountListPage (UA-04 view, UA-07 search by name/email, profile, status)."""
    controller = SearchUserAccountController()
    keyword, role, status = (request.args.get(k, "").strip() for k in ("q", "profile", "status"))
    found = controller.search(keyword, role, status)
    shown, page, pages = paginate(found, request.args.get("page", 1, type=int))
    return render_template("admin/accounts.html", nav="accounts",
                           accounts=shown, total=len(found), page=page, pages=pages,
                           profiles=controller.profile_choices(), statuses=controller.STATUSES,
                           keyword=keyword, role=role, status=status)


@admin_bp.route("/accounts/new", methods=["GET", "POST"])
@role_required("admin")
def create_account():
    """Boundary: CreateUserAccountPage (UA-03)."""
    error = None
    if request.method == "POST":
        f = request.form
        try:
            account = CreateUserAccountController().create(
                f.get("name"), f.get("email"), f.get("phone"), f.get("password"), f.get("profile"))
        except ValueError as exc:
            error = str(exc)
        else:
            flash(f"Account created for {account.email}.", "success")
            return redirect(url_for("admin.account", account_id=account.id))
    return render_template("admin/account_form.html", nav="accounts", account=None,
                           form=request.form, error=error, profiles=UserProfile.active())


@admin_bp.route("/accounts/<int:account_id>")
@role_required("admin")
def account(account_id, temporary_password=None):
    """Boundary: UserAccountPage (UA-04), with Edit, Suspend / Reactivate and Reset password."""
    try:
        details = ViewUserAccountController().view(account_id)
    except LookupError:
        abort(404)
    return render_template("admin/account.html", nav="accounts", a=details,
                           is_self=account_id == session["user_id"],
                           temporary_password=temporary_password)


@admin_bp.route("/accounts/<int:account_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_account(account_id):
    """Boundary: EditUserAccountPage (UA-05)."""
    try:
        details = ViewUserAccountController().view(account_id)
    except LookupError:
        abort(404)
    form, error = (request.form if request.method == "POST"
                   else {**details, "profile": details["role"]}), None
    if request.method == "POST":
        f = request.form
        try:
            UpdateUserAccountController().update(
                account_id, f.get("name"), f.get("email"), f.get("phone"), f.get("profile"),
                admin_id=session["user_id"])
        except ValueError as exc:
            error = str(exc)
        else:
            flash("Account updated.", "success")
            return redirect(url_for("admin.account", account_id=account_id))
    profiles = UserProfile.active()
    if all(p.key != details["role"] for p in profiles):  # keep a suspended profile selectable
        profiles.append(UserProfile.by_key(details["role"]))
    return render_template("admin/account_form.html", nav="accounts", account=details,
                           form=form, error=error, profiles=profiles)


def _account_action(account_id, action, done):
    try:
        action()
    except LookupError:
        abort(404)
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        flash(done, "success")
    return redirect(url_for("admin.account", account_id=account_id))


@admin_bp.route("/accounts/<int:account_id>/suspend", methods=["POST"])
@role_required("admin")
def suspend_account(account_id):
    """Boundary: confirmation dialog on UserAccountPage (UA-06)."""
    return _account_action(account_id, lambda: SuspendUserAccountController().suspend(
        session["user_id"], account_id), "Account suspended.")


@admin_bp.route("/accounts/<int:account_id>/reactivate", methods=["POST"])
@role_required("admin")
def reactivate_account(account_id):
    """Boundary: confirmation dialog on UserAccountPage (UA-13)."""
    return _account_action(account_id, lambda: ReactivateUserAccountController().reactivate(
        account_id), "Account reactivated.")


@admin_bp.route("/accounts/<int:account_id>/reset-password", methods=["POST"])
@role_required("admin")
def reset_password(account_id):
    """Boundary: Reset password button (UA-16). The temporary password is shown once, on this response only."""
    try:
        temporary = ResetPasswordController().reset(account_id)
    except LookupError:
        abort(404)
    return account(account_id, temporary_password=temporary)


# --- User profiles (UA-08 to UA-12) -----------------------------------------------

@admin_bp.route("/profiles")
@role_required("admin")
def profiles():
    """Boundary: UserProfileListPage (UA-09 view, UA-12 search)."""
    keyword = request.args.get("q", "").strip()
    return render_template("admin/profiles.html", nav="profiles",
                           profiles=SearchUserProfileController().search(keyword), keyword=keyword,
                           total=len(ViewUserProfileController().list_profiles()))


@admin_bp.route("/profiles/new", methods=["GET", "POST"])
@role_required("admin")
def create_profile():
    """Boundary: CreateUserProfilePage (UA-08)."""
    error = None
    if request.method == "POST":
        try:
            profile = CreateUserProfileController().create(
                request.form.get("name"), request.form.get("description"))
        except ValueError as exc:
            error = str(exc)
        else:
            flash(f"Profile “{profile.name}” created.", "success")
            return redirect(url_for("admin.profiles"))
    return render_template("admin/profile_form.html", nav="profiles", profile=None,
                           form=request.form, error=error)


@admin_bp.route("/profiles/<int:profile_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_profile(profile_id):
    """Boundary: EditUserProfilePage (UA-10)."""
    try:
        profile = ViewUserProfileController().view(profile_id)
    except LookupError:
        abort(404)
    form, error = (request.form if request.method == "POST"
                   else {"name": profile.name, "description": profile.description or ""}), None
    if request.method == "POST":
        try:
            UpdateUserProfileController().update(
                profile_id, request.form.get("name"), request.form.get("description"))
        except ValueError as exc:
            error = str(exc)
        else:
            flash("Profile updated.", "success")
            return redirect(url_for("admin.profiles"))
    return render_template("admin/profile_form.html", nav="profiles", profile=profile,
                           form=form, error=error)


@admin_bp.route("/profiles/<int:profile_id>/suspend", methods=["POST"])
@role_required("admin")
def suspend_profile(profile_id):
    """Boundary: confirmation dialog on UserProfileListPage (UA-11)."""
    try:
        profile = SuspendUserProfileController().suspend(profile_id)
    except LookupError:
        abort(404)
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        flash(f"Profile “{profile.name}” suspended.", "success")
    return redirect(url_for("admin.profiles"))


# --- Announcements (UA-18) --------------------------------------------------------

@admin_bp.route("/announcements", methods=["GET", "POST"])
@role_required("admin")
def announcements():
    """Boundary: AnnouncementsPage (UA-18): write one and see the past ones."""
    controller, error = SendAnnouncementController(), None
    if request.method == "POST":
        try:
            controller.send(session["user_id"], request.form.get("title"), request.form.get("message"))
        except ValueError as exc:
            error = str(exc)
        else:
            flash("Announcement sent to all users.", "success")
            return redirect(url_for("admin.announcements"))
    return render_template("admin/announcements.html", nav="announcements",
                           history=controller.history(), form=request.form, error=error)


# --- Reported IDPs (UA-17) --------------------------------------------------------

@admin_bp.route("/reports")
@role_required("admin")
def reports():
    """Boundary: ReportedProjectsPage (UA-17, shows reports from C-15)."""
    controller = ReviewReportsController()
    status = request.args.get("status", "open")
    return render_template(
        "admin/reports.html",
        nav="reports",
        reports=controller.list_reports(status),
        status=status if status in ("open", "resolved") else "open",
        open_count=controller.open_count(),
    )


@admin_bp.route("/reports/<int:report_id>/resolve", methods=["POST"])
@role_required("admin")
def resolve_report(report_id):
    try:
        ReviewReportsController().resolve(report_id, session["user_id"])
    except ValueError as error:
        flash(str(error))
    else:
        flash("Report marked as resolved.")
    return redirect(url_for("admin.reports"))


@admin_bp.route("/reports/<int:report_id>/remove", methods=["POST"])
@role_required("admin")
def remove_reported_project(report_id):
    """Boundary: Remove project button on ReportedProjectsPage (UA-17): hides it from customers."""
    try:
        report = ReviewReportsController().remove_idp(report_id, session["user_id"])
    except ValueError as error:
        flash(str(error), "error")
    else:
        flash(f"“{report.idp.title}” was removed from customers' view.", "success")
    return redirect(url_for("admin.reports"))


# --- Designer applications ------------------------------------------------------


@admin_bp.route("/applications")
@role_required("admin")
def applications():
    """Boundary: DesignerApplicationListPage."""
    controller = ReviewDesignerApplicationController()
    status = request.args.get("status", "pending")
    found = controller.list_applications(status)
    shown, page, pages = paginate(found, request.args.get("page", 1, type=int))
    return render_template(
        "admin/applications.html",
        nav="applications",
        applications=shown, total=len(found), page=page, pages=pages,
        status=status,
        pending=controller.pending_count(),
    )


@admin_bp.route("/applications/<int:application_id>")
@role_required("admin")
def application_detail(application_id):
    """Boundary: DesignerApplicationPage (approve or reject)."""
    application = ReviewDesignerApplicationController().get(application_id)
    if application is None:
        abort(404)
    return render_template("admin/application_detail.html", nav="applications",
                           application=application)


@admin_bp.route("/applications/<int:application_id>/approve", methods=["POST"])
@role_required("admin")
def approve_application(application_id):
    try:
        account = ReviewDesignerApplicationController().approve(application_id, session["user_id"])
    except ValueError as error:
        flash(str(error))
    else:
        flash(f"Approved. Designer account created for {account.email}.")
    return redirect(url_for("admin.applications"))


@admin_bp.route("/applications/<int:application_id>/reject", methods=["POST"])
@role_required("admin")
def reject_application(application_id):
    try:
        ReviewDesignerApplicationController().reject(
            application_id, session["user_id"], request.form.get("reason")
        )
    except ValueError as error:
        flash(str(error))
    else:
        flash("Application rejected.")
    return redirect(url_for("admin.applications"))
