from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import secrets
from hmac import compare_digest
from app.control.update_company_controller import UpdateCompanyController
from app.control.delete_company_controller import DeleteCompanyController
from app.boundary import role_required
from app.control.view_enquiries_controller import ViewEnquiriesController
from app.control.add_company_controller import AddCompanyController
from app.control.view_company_controller import ViewCompanyController
from app.control.add_idp_controller import AddIDPController
from app.control.edit_project_controller import EditProjectController
from app.control.delete_project_controller import DeleteProjectController
from app.control.view_portfolio_controller import ViewPortfolioController
from app.control.search_portfolio_controller import SearchPortfolioController
from app.control.view_idp_statistics_controller import ViewIDPStatisticsController
from app.control.view_designer_account_controller import ViewDesignerAccountController
from app.control.update_designer_account_controller import UpdateDesignerAccountController
from app.control.remove_project_photo_controller import RemoveProjectPhotoController
from app.control.view_trends_controller import ViewTrendsController

designer_bp = Blueprint("designer", __name__, url_prefix="/designer")


@designer_bp.route("/")
@role_required("designer")
def home():
    return render_template("designer/home.html",
                           enquiry_count=ViewEnquiriesController().count(session["user_id"]))


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

def _company_token():
    if "designer_csrf" not in session:
        session["designer_csrf"] = secrets.token_hex(32)

    return session["designer_csrf"]


def _check_company_token():
    expected = session.get("designer_csrf", "")
    supplied = request.form.get("csrf_token", "")

    if not expected or not compare_digest(
        expected.encode(),
        supplied.encode(),
    ):
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
        csrf_token=_company_token(),
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
        csrf_token=_company_token(),
    )

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
        csrf_token=_company_token(),
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
        csrf_token=_company_token(),
    )

@designer_bp.route(
    "/portfolio/<int:idp_id>/delete",
    methods=["GET", "POST"],
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

        if request.form.get("confirm") != "delete":
            return redirect(
                url_for("customer.project", idp_id=idp_id)
            )

        controller.delete(session["user_id"], idp_id)

        flash("Project deleted successfully.", "success")

        return redirect(
            url_for(
                "customer.designer_profile",
                designer_id=session["user_id"],
                all=1,
            ) + "#projects"
        )

    return render_template(
        "designer/delete_project.html",
        project=project,
        csrf_token=_company_token(),
    )

@designer_bp.route("/portfolio")
@role_required("designer")
def portfolio():
    keyword = request.args.get("q", "").strip()

    try:
        if keyword:
            projects = SearchPortfolioController().search(
                session["user_id"],
                keyword,
            )
        else:
            projects = ViewPortfolioController().view(
                session["user_id"]
            )

    except LookupError:
        abort(404)

    return render_template(
        "designer/portfolio.html",
        projects=projects,
        keyword=keyword,
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


@designer_bp.route("/profile")
@role_required("designer")
def profile():
    controller = ViewDesignerAccountController()

    try:
        account = controller.view(
            session["user_id"]
        )

        registration_status = controller.registration_status(
            session["user_id"]
        )

    except LookupError:
        abort(404)

    return render_template(
        "designer/profile.html",
        account=account,
        registration_status=registration_status,
    )

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
        csrf_token=_company_token(),
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