from datetime import datetime

from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    current_app
)

from app.control.update_company_controller import UpdateCompanyController
from app.control.delete_company_controller import DeleteCompanyController
from app.boundary import role_required, safe_next
from app.control.view_enquiries_controller import ViewEnquiriesController
from app.control.add_company_controller import AddCompanyController
from app.control.view_company_controller import ViewCompanyController
from app.control.add_idp_controller import AddIDPController
from app.control.edit_project_controller import EditProjectController
from app.control.delete_project_controller import DeleteProjectController
from app.control.view_portfolio_controller import ViewPortfolioController
from app.control.view_idp_statistics_controller import ViewIDPStatisticsController
from app.control.view_designer_account_controller import ViewDesignerAccountController
from app.control.update_designer_account_controller import UpdateDesignerAccountController
from app.control.remove_project_photo_controller import RemoveProjectPhotoController
from app.control.view_trends_controller import ViewTrendsController

from app.control.set_idp_status_controller import SetIDPStatusController
from app.control.update_designer_profile_controller import UpdateDesignerProfileController
from app.control.view_designer_dashboard_controller import ViewDesignerDashboardController
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
    try:
        messages = ViewEnquiriesController().view(
            session["user_id"]
        )
    except LookupError:
        abort(404)

    return render_template(
        "designer/enquiries.html",
        enquiries=messages,
    )

@designer_bp.after_request
def prevent_designer_page_caching(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@designer_bp.route("/company/add", methods=["GET", "POST"])
@role_required("designer")
def add_company():
    controller = AddCompanyController()
    account_id = session["user_id"]

    if controller.has_company(account_id):
        flash(
            "You already have company information. Edit it here.",
            "info",
        )

        return redirect(
            url_for("designer.edit_company")
        )

    if request.method == "POST":
        try:
            controller.add(account_id, request.form)

        except ValueError as error:
            flash(str(error), "error")

        else:
            flash(
                "Company information added successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "customer.designer_profile",
                    designer_id=account_id,
                )
            )

    return render_template(
        "designer/add_company.html",
        form=request.form,
    )


@designer_bp.route("/company")
@role_required("designer")
def company():
    try:
        company_information = ViewCompanyController().view(
            session["user_id"]
        )
    except LookupError:
        abort(404)

    if company_information:
        return redirect(
            url_for(
                "customer.designer_profile",
                designer_id=session["user_id"],
            )
        )

    return render_template(
        "designer/company.html",
        company=None,
    )



def _check_company_token():
    if not current_app.config.get("WTF_CSRF_ENABLED", True):
        return

    try:
        validate_csrf(request.form.get("csrf_token"))
    except ValidationError:
        abort(
            400,
            description="Form expired. Reload the page and try again.",
        )


@designer_bp.route("/company/edit", methods=["GET", "POST"])
@role_required("designer")
def edit_company():
    try:
        existing = ViewCompanyController().view(
            session["user_id"]
        )

        if not existing:
            return redirect(url_for("designer.add_company"))

        if request.method == "POST":
            _check_company_token()

            try:
                UpdateCompanyController().update(
                    session["user_id"],
                    request.form,
                    request.files.get("profile_photo"),
                )
            except ValueError as error:
                flash(str(error), "error")

            else:
                flash(
                    "Company information updated successfully.",
                    "success",
                )
                return redirect(url_for("designer.company"))

    except LookupError:
        abort(404)

    if request.method == "POST":
        form = request.form
    else:
        form = {
            field: getattr(existing, field, "") or ""
            for field in (
                "company_name",
                "description",
                "address",
                "phone",
                "email",
            )
        }

    return render_template(
        "designer/edit_company.html",
        form=form,
    )


@designer_bp.route("/company/delete", methods=["GET", "POST"])
@role_required("designer")
def delete_company():
    try:
        existing = ViewCompanyController().view(
            session["user_id"]
        )

        if not existing:
            return redirect(url_for("designer.company"))

        if request.method == "POST":
            _check_company_token()

            if request.form.get("confirm") != "delete":
                return redirect(url_for("designer.company"))

            DeleteCompanyController().delete(
                session["user_id"]
            )

            flash("Company information deleted.", "success")
            return redirect(url_for("designer.company"))

    except LookupError:
        abort(404)

    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("designer.company"))

    return render_template(
        "designer/delete_company.html",
        company=existing,
    )

@designer_bp.route("/portfolio/new", methods=["GET", "POST"])
@designer_bp.route("/portfolio/add", methods=["GET", "POST"])
@role_required("designer")
def add_project():
    controller = AddIDPController()

    if request.method == "POST":
        _check_company_token()

        try:
            project = controller.add(
                session["user_id"],
                request.form,
                request.files.getlist("photos"),
            )

        except LookupError:
            abort(404)

        except ValueError as error:
            flash(str(error), "error")

        else:
            flash(
                f'Project "{project.title}" added successfully.',
                "success",
            )

            return redirect(
                url_for(
                    "customer.designer_profile",
                    designer_id=session["user_id"],
                    all=1,
                ) + "#projects"
            )

    return render_template(
        "designer/add_project.html",
        categories=controller.CATEGORIES,
        form=request.form,
    )

@designer_bp.route(
    "/portfolio/<int:idp_id>/edit",
    methods=["GET", "POST"],
)
@role_required("designer")
def edit_project(idp_id):
    controller = EditProjectController()

    try:
        project = controller.get_project(
            session["user_id"],
            idp_id,
        )

    except LookupError:
        abort(404)

    if request.method == "POST":
        _check_company_token()

        try:
            controller.update(
                session["user_id"],
                idp_id,
                request.form,
                request.files.getlist("photos"),
            )

        except ValueError as error:
            flash(str(error), "error")

        else:
            flash("Project updated successfully.", "success")

            return redirect(
                url_for(
                    "customer.project",
                    idp_id=idp_id,
                )
            )

    if request.method == "POST":
        form = request.form
    else:
        form = {
            "title": project.title,
            "description": project.description or "",
            "category": project.category,
            "status": "current" if project.is_current else "past",
        }

    return render_template(
        "designer/add_project.html",
        categories=controller.CATEGORIES,
        form=form,
        editing=True,
        project=project,
    )

@designer_bp.route(
    "/portfolio/<int:idp_id>/delete/confirm",
    methods=["GET"],
    endpoint="confirm_delete_project",
)
@designer_bp.route(
    "/portfolio/<int:idp_id>/delete",
    methods=["POST"],
)
@role_required("designer")
def delete_project(idp_id):
    controller = DeleteProjectController()

    try:
        project = controller.get_project(
            session["user_id"],
            idp_id,
        )
    except LookupError:
        abort(404)

    if request.method == "POST":
        _check_company_token()

        if request.form.get("confirm", "delete") != "delete":
            return redirect(
                url_for("customer.project", idp_id=idp_id)
            )

        controller.delete(session["user_id"], idp_id)

        flash("Project deleted successfully.", "success")
        return redirect(url_for("designer.portfolio"))

    return render_template(
        "designer/delete_project.html",
        project=project,
    )


@designer_bp.route("/statistics")
@role_required("designer")
def statistics():
    try:
        projects = ViewIDPStatisticsController().view(
            session["user_id"]
        )

    except LookupError:
        abort(404)

    return render_template(
        "designer/statistics.html",
        projects=projects,
    )


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
                           updated=request.args.get("updated") == "1",
                           registration_status=ViewDesignerAccountController().registration_status(account.id))

@designer_bp.route(
    "/profile/edit",
    methods=["GET", "POST"],
)
@role_required("designer")
def edit_profile():
    try:
        account = ViewDesignerAccountController().view(
            session["user_id"]
        )

        if request.method == "POST":
            _check_company_token()

            try:
                account = UpdateDesignerAccountController().update(
                    session["user_id"],
                    request.form,
                )

            except ValueError as error:
                flash(str(error), "error")

            else:
                session["name"] = account.name

                flash(
                    "Your profile has been updated successfully.",
                    "success",
                )

                return redirect(
                    url_for("designer.profile")
                )

    except LookupError:
        abort(404)

    if request.method == "POST":
        form = request.form
    else:
        form = {
            "name": account.name or "",
            "email": account.email,
            "phone": account.phone or "",
        }

    return render_template(
        "designer/edit_profile.html",
        form=form,
    )

@designer_bp.route(
    "/portfolio/<int:idp_id>/photos/<int:photo_id>/delete",
    methods=["POST"],
)
@role_required("designer")
def remove_project_photo(idp_id, photo_id):
    _check_company_token()

    try:
        RemoveProjectPhotoController().remove(
            session["user_id"],
            idp_id,
            photo_id,
        )

    except LookupError:
        abort(404)

    flash("Photo removed.", "success")

    return redirect(
        url_for(
            "designer.edit_project",
            idp_id=idp_id,
        )
    )


@designer_bp.errorhandler(413)
def photo_upload_too_large(error):
    flash(
        "Upload is too large. Use at most 10 photos, "
        "each 5 MB or smaller.",
        "error",
    )

    return redirect(url_for("designer.portfolio"))

@designer_bp.route("/trends")
@role_required("designer")
def trends():
    try:
        days = int(request.args.get("days", "7"))
    except ValueError:
        abort(400, description="Select 7 or 30 days.")

    try:
        data = ViewTrendsController().view(
            session["user_id"],
            days,
        )
    except LookupError:
        abort(404)
    except ValueError as error:
        abort(400, description=str(error))

    return render_template(
        "designer/trends.html",
        **data,
    )
