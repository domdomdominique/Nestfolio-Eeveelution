from datetime import date

from flask import (Blueprint, Response, abort, flash, redirect, render_template, request,
                   url_for)

from app.boundary import role_required
from app.control.create_category_controller import CreateCategoryController
from app.control.delete_category_controller import DeleteCategoryController
from app.control.download_report_controller import DownloadReportController
from app.control.generate_report_controller import GenerateReportController
from app.control.search_category_controller import SearchCategoryController
from app.control.send_announcement_controller import SendAnnouncementController
from app.control.update_category_controller import UpdateCategoryController
from app.control.view_category_controller import ViewCategoryController

platform_bp = Blueprint("platform", __name__, url_prefix="/platform")


@platform_bp.after_request
def no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@platform_bp.route("/")
@role_required("platform")
def home():
    """Boundary: PlatformDashboardPage (summary of today, plus announcements from UA-18)."""
    return render_template(
        "platform/home.html", nav="dashboard",
        today=GenerateReportController().daily(date.today()),
        categories=ViewCategoryController().list_categories(),
        announcements=SendAnnouncementController().latest(3))


# --- IDP categories (PM-03 to PM-07) ------------------------------------------------

@platform_bp.route("/categories")
@role_required("platform")
def categories():
    """Boundary: CategoryListPage (PM-04 view, PM-07 search)."""
    keyword = (request.args.get("q") or "").strip()
    found = SearchCategoryController().search(keyword)
    return render_template("platform/categories.html", nav="categories",
                           categories=found, keyword=keyword,
                           total=len(ViewCategoryController().list_categories()))


@platform_bp.route("/categories/<int:category_id>")
@role_required("platform")
def view_category(category_id):
    """Boundary: CategoryDetailPage (PM-04 AC3: open a category to see its details)."""
    try:
        category = ViewCategoryController().view(category_id)
    except LookupError:
        abort(404)
    return render_template("platform/category_detail.html", nav="categories", category=category)


@platform_bp.route("/categories/new", methods=["GET", "POST"])
@role_required("platform")
def create_category():
    """Boundary: CreateCategoryPage (PM-03)."""
    error = None
    if request.method == "POST":
        try:
            category = CreateCategoryController().create(
                request.form.get("name"), request.form.get("description"))
        except ValueError as exc:
            error = str(exc)
        else:
            flash(f"Category “{category.name}” created.", "success")
            return redirect(url_for("platform.categories"))
    return render_template("platform/category_form.html", nav="categories",
                           category=None, form=request.form, error=error)


@platform_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@role_required("platform")
def edit_category(category_id):
    """Boundary: EditCategoryPage (PM-05)."""
    try:
        category = ViewCategoryController().view(category_id)
    except LookupError:
        abort(404)
    form, error = request.form if request.method == "POST" else category_form(category), None
    if request.method == "POST":
        try:
            UpdateCategoryController().update(
                category_id, request.form.get("name"), request.form.get("description"))
        except ValueError as exc:
            error = str(exc)
        else:
            flash("Category updated.", "success")
            return redirect(url_for("platform.categories"))
    return render_template("platform/category_form.html", nav="categories",
                           category=category, form=form, error=error)


def category_form(category):
    return {"name": category.name, "description": category.description or ""}


@platform_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@role_required("platform")
def delete_category(category_id):
    """Boundary: confirmation dialog on CategoryListPage posts here (PM-06)."""
    try:
        name = DeleteCategoryController().delete(category_id)
    except LookupError:
        abort(404)
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        flash(f"Category “{name}” deleted.", "success")
    return redirect(url_for("platform.categories"))


# --- Reports (PM-08 to PM-11) -------------------------------------------------------

def default_value(kind):
    today = date.today()
    return today.strftime("%Y-%m") if kind == "monthly" else today.isoformat()


@platform_bp.route("/reports")
@role_required("platform")
def reports():
    """Boundary: ReportsPage (PM-08 daily, PM-09 weekly, PM-10 monthly)."""
    kind = request.args.get("kind", "daily")
    if kind not in GenerateReportController.KINDS:
        kind = "daily"
    value = request.args.get("value") or default_value(kind)
    report = error = None
    try:
        report = GenerateReportController().generate(kind, value)
    except ValueError as exc:
        error = str(exc)
    return render_template("platform/reports.html", nav="reports", kind=kind,
                           value=value, report=report, error=error)


@platform_bp.route("/reports/download")
@role_required("platform")
def download_report():
    """Boundary: Download as PDF or Excel buttons on ReportsPage (PM-11)."""
    try:
        report = GenerateReportController().generate(
            request.args.get("kind"), request.args.get("value"))
        name, content_type, data = DownloadReportController().download(
            report, request.args.get("format"))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("platform.reports"))
    return Response(data, content_type=content_type,
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
