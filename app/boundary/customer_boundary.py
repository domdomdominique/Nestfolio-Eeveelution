from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from io import BytesIO
from flask import send_file
from app.control.update_company_controller import UpdateCompanyController

from app.control.view_idp_photo_controller import ViewIDPPhotoController

from app.boundary import role_required, safe_next
from app.control.send_announcement_controller import SendAnnouncementController
from app.control.browse_designers_controller import BrowseDesignersController
from app.control.change_password_controller import ChangePasswordController
from app.control.remove_favourite_controller import RemoveFavouriteController
from app.control.report_idp_controller import ReportIDPController
from app.control.save_favourite_controller import SaveFavouriteController
from app.control.search_favourites_controller import SearchFavouritesController
from app.control.search_idp_controller import SearchIDPController
from app.control.send_enquiry_controller import SendEnquiryController
from app.control.update_profile_controller import UpdateProfileController
from app.control.validate_session_controller import ValidateSessionController
from app.entity.user_account import UserAccount
from app.control.view_designer_profile_controller import ViewDesignerProfileController
from app.control.enquiry_inbox_controller import EnquiryInboxController
from app.control.reply_to_enquiry_controller import ReplyToEnquiryController
from app.control.view_favourites_controller import ViewFavouritesController
from app.control.view_idp_controller import ViewIDPController
from app.control.view_my_enquiries_controller import ViewMyEnquiriesController
from app.control.view_profile_controller import ViewProfileController

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")

PAGE_SIZE = 12


def _customer_id():
    """The logged-in customer's id, or None for visitors and other roles."""
    return session["user_id"] if session.get("role") == "customer" else None


def _back(default):
    """Where to go after a form post: the page's own `next` field, if safe."""
    return redirect(safe_next(request.form.get("next")) or default)


# --- Browse projects (C-04 search, C-05 filter, C-17 sort) ----------------------

@customer_bp.after_request
def no_store_when_logged_in(response):
    """Back after logging out must not show a logged-in page from the browser cache."""
    if session.get("user_id"):
        response.headers["Cache-Control"] = "no-store"
    return response


@customer_bp.route("/")
def home():
    """Boundary: BrowseProjectsPage (public; also the customer's home after login)."""
    search = SearchIDPController()
    keyword = request.args.get("q", "").strip()
    # Categories come from the sidebar checkboxes, or one from the landing page dropdown
    categories = request.args.getlist("category")
    # Status is two checkboxes; ticking both (or neither) means all projects
    statuses = request.args.getlist("status")
    status = statuses[0] if len(statuses) == 1 else None
    sort = search.clean_sort(request.args.get("sort"))
    results = search.browse(keyword, categories, status, sort)

    pages = max(1, -(-len(results) // PAGE_SIZE))
    page = min(max(request.args.get("page", 1, type=int), 1), pages)
    customer_id = _customer_id()
    return render_template(
        "customer/browse.html",
        announcements=SendAnnouncementController().latest(3) if customer_id else [],  # UA-18
        projects=results[(page - 1) * PAGE_SIZE: page * PAGE_SIZE],
        total=len(results), page=page, pages=pages,
        keyword=keyword, categories=[c for c in categories if c], status=status, sort=sort,
        sorts=search.SORTS, category_counts=search.category_counts(),
        status_counts=search.status_counts(),
        saved_ids=ViewFavouritesController().saved_ids(customer_id) if customer_id else set(),
    )


# --- One project (C-06 view, C-15 report) -----------------------------------------

@customer_bp.route("/projects/<int:idp_id>")
def project(idp_id):
    """Boundary: ProjectDetailPage (C-06)."""
    try:
            page = ViewIDPController().view(
            idp_id,
            _customer_id(),
            viewer_role=session.get("role"),
            record=request.method == "GET",
        )
    except LookupError:
        # Deleted, or the designer is suspended: C-06 AC4 "Project not available"
        return render_template("customer/project_unavailable.html"), 404
    return render_template("customer/project.html",
                           reasons=ReportIDPController().reasons(), **page)


@customer_bp.route("/projects/<int:idp_id>/report", methods=["POST"])
@role_required("customer")
def report_project(idp_id):
    """Boundary: ReportProjectDialog (C-15)."""
    try:
        ReportIDPController().report(session["user_id"], idp_id,
                                     request.form.get("reason"), request.form.get("details"))
    except LookupError:
        abort(404)
    except ValueError as error:
        flash(str(error), "error")
    else:
        flash("Thanks. Your report has been sent to our admin team for review.", "success")
    return redirect(url_for("customer.project", idp_id=idp_id))


# --- Favourites (C-07 to C-10) -------------------------------------------------

@customer_bp.route("/favourites")
@role_required("customer")
def favourites():
    """Boundary: MyFavouritesPage (C-08 view, C-09 search)."""
    view = ViewFavouritesController()
    keyword = request.args.get("q", "").strip()
    sort = view.clean_sort(request.args.get("sort"))
    if keyword:
        projects = SearchFavouritesController().search(session["user_id"], keyword, sort)
    else:
        projects = view.view(session["user_id"], sort)
    return render_template(
        "customer/favourites.html", projects=projects, keyword=keyword, sort=sort,
        sorts=view.sort_options(), total=view.count(session["user_id"]),
    )


@customer_bp.route("/favourites/<int:idp_id>", methods=["POST"])
@role_required("customer")
def save_favourite(idp_id):
    """Boundary: heart / 'Save to favourites' button on an IDP (C-07)."""
    try:
        idp, added = SaveFavouriteController().save(session["user_id"], idp_id)
    except LookupError:
        abort(404)
    if added:
        flash(f"Saved “{idp.title}” to your favourites.", "success")
    else:
        flash(f"“{idp.title}” is already in your favourites.", "success")
    return _back(url_for("customer.favourites"))


@customer_bp.route("/favourites/<int:idp_id>/remove", methods=["POST"])
@role_required("customer")
def remove_favourite(idp_id):
    """Boundary: filled heart on a saved IDP card (C-10). Offers an Undo."""
    try:
        idp = RemoveFavouriteController().remove(session["user_id"], idp_id)
    except LookupError:
        abort(404)
    flash({"text": f"Removed “{idp.title}” from favourites", "undo_idp": idp.id}, "toast")
    return _back(url_for("customer.favourites"))


# --- My profile (C-11 view, C-12 update, C-14 change password) ------------------

@customer_bp.route("/profile", methods=["GET", "POST"])
@role_required("customer")
def profile():
    """Boundary: MyProfilePage (C-11 view, C-12 update)."""
    account = ViewProfileController().view(session["user_id"])
    form = None
    if request.method == "POST":
        f = request.form
        try:
            UpdateProfileController().update(account.id, f.get("first_name"), f.get("last_name"),
                                             f.get("email"), f.get("phone"),
                                             f.get("current_password"))
        except ValueError as error:
            flash(str(error), "error")
            form = f  # keep what they typed (the password field is never filled back in)
        else:
            session["name"] = account.name
            return redirect(url_for("customer.profile", updated=1))
    return render_template("customer/profile.html", account=account, form=form,
                           updated=request.args.get("updated") == "1")


@customer_bp.route("/profile/password", methods=["POST"])
@role_required("customer")
def change_password():
    """Boundary: Change password card on MyProfilePage (C-14)."""
    f = request.form
    try:
        ChangePasswordController().change(session["user_id"], f.get("current_password"),
                                          f.get("new_password"), f.get("confirm_password"))
    except ValueError as error:
        flash(str(error), "password-error")
    else:
        # The new password changes the session fingerprint; keep this browser logged in
        session["auth"] = ValidateSessionController().token_for(UserAccount.get(session["user_id"]))
        flash("Password updated.", "success")
    return redirect(url_for("customer.profile") + "#password")


# --- Designers (C-13 view profile, C-16 contact) ---------------------------------

@customer_bp.route("/designers")
def designers():
    """Boundary: BrowseDesignersPage."""
    return render_template("customer/designers.html",
                           designers=BrowseDesignersController().list_designers())


@customer_bp.route("/designers/<int:designer_id>")
def designer_profile(designer_id):
    """Boundary: DesignerProfilePage (C-13)."""
    try:
        page = ViewDesignerProfileController().view(
            designer_id, request.args.get("status"), _customer_id())
    except LookupError:
        abort(404)
    return render_template("customer/designer_profile.html",
                           show_all=request.args.get("all") == "1", **page)


@customer_bp.route("/designers/<int:designer_id>/enquiry", methods=["POST"])
@role_required("customer")
def send_enquiry(designer_id):
    """Boundary: 'Send enquiry' in the messaging page's new-conversation pane (C-16).
    When it is sent, the new conversation opens in My enquiries."""
    f = request.form
    idp_id = f.get("idp_id", type=int)
    controller = SendEnquiryController()
    try:
        designer = controller.send(session["user_id"], designer_id, f.get("name"), f.get("contact"),
                                   f.get("message"), idp_id)
    except LookupError:
        abort(404)
    except ValueError as error:
        # Show the error next to the form and keep what the customer typed
        flash(str(error), "error")
        designer, idp, _ = controller.start(session["user_id"], designer_id, idp_id)
        return _enquiries_page(compose={"designer": designer, "idp": idp, "name": f.get("name", ""),
                                        "contact": f.get("contact", ""), "message": f.get("message", "")})
    flash(f"Your enquiry has been sent to {designer.display_name}. Their reply will appear in My enquiries.", "success")
    new = controller.latest(session["user_id"], designer.id)
    return redirect(url_for("customer.my_enquiries", id=new.id))


# --- My enquiries: the designer's replies (ID-21 AC5) -----------------------------------

def _enquiries_page(compose=None):
    """The customer's two-pane messaging page; compose fills the right pane with a new enquiry."""
    try:
        enquiries = ViewMyEnquiriesController().view(session["user_id"])
    except LookupError:
        abort(404)
    inbox = EnquiryInboxController().open(
        session["user_id"], enquiries,
        selected_id=request.args.get("id", type=int),
        show=request.args.get("show", "all"),
        search=request.args.get("q", ""),
    )
    if compose:
        inbox["selected"] = None  # nothing else is open while writing a new enquiry
    return render_template("customer/enquiries.html", nav="enquiries", total=len(enquiries),
                           compose=compose, **inbox)


@customer_bp.route("/enquiries")
@role_required("customer")
def my_enquiries():
    """Boundary: MyEnquiriesPage, the same two-pane inbox the designer has, from the customer's side."""
    return _enquiries_page()


@customer_bp.route("/enquiries/new")
@role_required("customer")
def new_enquiry():
    """Boundary: 'Send enquiry' button on a project or designer page (C-16 AC1).
    Opens the messaging page ready to write to that designer, or the existing conversation."""
    try:
        designer, idp, existing = SendEnquiryController().start(
            session["user_id"], request.args.get("designer_id", type=int), request.args.get("idp_id", type=int))
    except LookupError:
        abort(404)
    if existing is not None:
        return redirect(url_for("customer.my_enquiries", id=existing.id))
    account = UserAccount.get(session["user_id"])
    return _enquiries_page(compose={"designer": designer, "idp": idp, "name": account.name or "",
                                    "contact": account.email, "message": ""})


@customer_bp.route("/enquiries/<int:enquiry_id>/reply", methods=["POST"])
@role_required("customer")
def reply_to_designer(enquiry_id):
    """Boundary: the customer answers a designer's reply."""
    try:
        reply = ReplyToEnquiryController().reply(session["user_id"], enquiry_id, request.form.get("message"))
    except LookupError:
        abort(404)
    except ValueError as error:
        flash(str(error), "error")
    else:
        flash(f"Message sent to {reply.enquiry.designer.display_name}.", "success")
    args = {k: v for k, v in (("show", request.form.get("show")), ("q", request.form.get("q"))) if v and v != "all"}
    return redirect(url_for("customer.my_enquiries", id=enquiry_id, **args))


@customer_bp.route("/photos/<int:photo_id>")
def project_photo(photo_id):
    try:
        photo = ViewIDPPhotoController().view(photo_id)

    except LookupError:
        abort(404)

    response = send_file(
        BytesIO(photo.data),
        mimetype=photo.content_type,
        download_name=photo.filename,
        max_age=0,
    )

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"

    return response


@customer_bp.route("/designers/<int:designer_id>/company-photo")
def company_photo(designer_id):
    try:
        photo = UpdateCompanyController().view_photo(designer_id)
    except LookupError:
        abort(404)

    response = send_file(
        BytesIO(photo.data),
        mimetype=photo.content_type,
        download_name=photo.filename,
        max_age=0,
    )

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"

    return response
