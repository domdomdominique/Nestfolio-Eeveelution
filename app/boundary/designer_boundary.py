from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app.boundary import role_required, safe_next
from app.control.add_idp_controller import AddIDPController
from app.control.delete_idp_controller import DeleteIDPController
from app.control.edit_idp_controller import EditIDPController
from app.control.set_idp_status_controller import SetIDPStatusController
from app.control.update_designer_profile_controller import UpdateDesignerProfileController
from app.control.view_designer_dashboard_controller import ViewDesignerDashboardController
from app.control.view_enquiries_controller import ViewEnquiriesController
from app.control.view_portfolio_controller import ViewPortfolioController
from app.control.view_profile_controller import ViewProfileController

designer_bp = Blueprint("designer", __name__, url_prefix="/designer")


@designer_bp.app_template_filter("ago")
def ago(moment):
    """'2 days ago' style text for a datetime."""
    seconds = int((datetime.now() - moment).total_seconds())
    for unit, size in (("year", 31536000), ("month", 2592000), ("week", 604800),
                       ("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size:
            count = seconds // size
            return f"{count} {unit}{'s' if count != 1 else ''} ago"
    return "Just now"


# --- Dashboard ---------------------------------------------------------------------

@designer_bp.route("/")
@role_required("designer")
def home():
    """Boundary: DesignerDashboardPage (landing page after ID-01 login)."""
    return render_template("designer/home.html", nav="dashboard",
                           **ViewDesignerDashboardController().view(session["user_id"]))


# --- Portfolio (ID-06 to ID-12) ----------------------------------------------------

@designer_bp.route("/portfolio")
@role_required("designer")
def portfolio():
    """Boundary: MyPortfolioPage (ID-07 list, ID-08 search, ID-13/14 counts, ID-11 status)."""
    page = ViewPortfolioController().view(
        session["user_id"], request.args.get("q"), request.args.get("status"),
        request.args.get("category"), request.args.get("page", 1, type=int))
    return render_template("designer/portfolio.html", nav="portfolio", **page)


@designer_bp.route("/portfolio/new", methods=["GET", "POST"])
@role_required("designer")
def add_project():
    """Boundary: AddProjectPage (ID-06)."""
    controller = AddIDPController()
    form = {"status": "current"}
    if request.method == "POST":
        form = request.form
        try:
            idp = controller.add(session["user_id"], form.get("title"), form.get("description"),
                                 form.get("category"), form.get("status"))
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash(f"“{idp.title}” has been added to your portfolio.", "success")
            return redirect(url_for("designer.portfolio"))
    return render_template("designer/project_form.html", nav="portfolio", idp=None,
                           form=form, categories=controller.categories())


@designer_bp.route("/portfolio/<int:idp_id>/edit", methods=["GET", "POST"])
@role_required("designer")
def edit_project(idp_id):
    """Boundary: EditProjectPage (ID-09)."""
    controller = EditIDPController()
    try:
        idp = controller.get(session["user_id"], idp_id)
    except LookupError:
        abort(404)
    form = {"title": idp.title, "description": idp.description, "category": idp.category,
            "status": "current" if idp.is_current else "past"}
    if request.method == "POST":
        form = request.form
        try:
            controller.edit(session["user_id"], idp_id, form.get("title"), form.get("description"),
                            form.get("category"), form.get("status"))
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash("Your changes have been saved.", "success")
            return redirect(url_for("designer.portfolio"))
    return render_template("designer/project_form.html", nav="portfolio", idp=idp,
                           form=form, categories=controller.categories())


@designer_bp.route("/portfolio/<int:idp_id>/delete", methods=["POST"])
@role_required("designer")
def delete_project(idp_id):
    """Boundary: Delete project dialog (ID-10). The page asks for confirmation before posting."""
    try:
        title = DeleteIDPController().delete(session["user_id"], idp_id)
    except LookupError:
        abort(404)
    flash(f"“{title}” has been deleted.", "success")
    return redirect(url_for("designer.portfolio"))


@designer_bp.route("/portfolio/<int:idp_id>/status", methods=["POST"])
@role_required("designer")
def set_status(idp_id):
    """Boundary: Mark project as Current / Past menu (ID-11)."""
    try:
        SetIDPStatusController().set(session["user_id"], idp_id, request.form.get("status"))
    except LookupError:
        abort(404)
    except ValueError as error:
        flash(str(error), "error")
    return redirect(safe_next(request.form.get("next")) or url_for("designer.portfolio"))


# --- Enquiries (ID-21) -------------------------------------------------------------

@designer_bp.route("/enquiries")
@role_required("designer")
def enquiries():
    """Boundary: MyEnquiriesPage (ID-21, shows enquiries sent through C-16)."""
    return render_template("designer/enquiries.html", nav="enquiries",
                           enquiries=ViewEnquiriesController().view(session["user_id"]))


# --- My profile (ID-17 view, ID-18 edit) -------------------------------------------

@designer_bp.route("/profile", methods=["GET", "POST"])
@role_required("designer")
def profile():
    """Boundary: MyProfilePage (ID-17, ID-18)."""
    account = ViewProfileController().view(session["user_id"])
    form = None
    if request.method == "POST":
        form = request.form
        try:
            UpdateDesignerProfileController().update(
                account.id, form.get("name"), form.get("email"), form.get("phone"),
                form.get("current_password"))
        except ValueError as error:
            flash(str(error), "error")
        else:
            session["name"] = account.name
            return redirect(url_for("designer.profile", updated=1))
    return render_template("designer/profile.html", nav="profile", account=account, form=form,
                           updated=request.args.get("updated") == "1")
