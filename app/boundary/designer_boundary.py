from flask import Blueprint, render_template, session

from app.boundary import role_required
from app.control.view_enquiries_controller import ViewEnquiriesController

designer_bp = Blueprint("designer", __name__, url_prefix="/designer")


@designer_bp.route("/")
@role_required("designer")
def home():
    return render_template("designer/home.html",
                           enquiry_count=ViewEnquiriesController().count(session["user_id"]))


@designer_bp.route("/enquiries")
@role_required("designer")
def enquiries():
    """Boundary: MyEnquiriesPage (ID-21, shows enquiries sent through C-16)."""
    return render_template("designer/enquiries.html",
                           enquiries=ViewEnquiriesController().view(session["user_id"]))
