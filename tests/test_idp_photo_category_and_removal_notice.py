"""10 MB IDP photos, required category backgrounds (PM-03) and the designer's removal notice (UA-17)."""
import io

import pytest
from werkzeug.datastructures import FileStorage

from conftest import png_bytes, png_field, png_upload

from app.control.create_category_controller import CreateCategoryController
from app.control.portfolio_validation import IDP_MAX_PHOTO_BYTES, MAX_PHOTO_BYTES, validated_photos
from app.control.report_idp_controller import ReportIDPController
from app.control.review_reports_controller import ReviewReportsController
from app.control.update_category_controller import UpdateCategoryController
from app.entity.announcement import Announcement
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.idp_category import IDPCategory
from app.entity.user_account import UserAccount


def padded_png(total_bytes):
    """A valid PNG padded with trailing bytes to the given size (Pillow ignores data after IEND)."""
    data = png_bytes()
    return FileStorage(io.BytesIO(data + b"\0" * (total_bytes - len(data))), filename="big.png")


# --- IDP photos up to 10 MB --------------------------------------------------------

def test_idp_photos_accept_up_to_10_mb():
    assert IDP_MAX_PHOTO_BYTES == 10 * 1024 * 1024
    assert validated_photos([padded_png(8 * 1024 * 1024)], max_bytes=IDP_MAX_PHOTO_BYTES)
    with pytest.raises(ValueError, match="10 MB or smaller"):
        validated_photos([padded_png(IDP_MAX_PHOTO_BYTES + 1)], max_bytes=IDP_MAX_PHOTO_BYTES)


def test_company_photos_keep_the_5_mb_limit():
    with pytest.raises(ValueError, match="5 MB or smaller"):
        validated_photos([padded_png(MAX_PHOTO_BYTES + 1)])


def test_add_project_page_shows_the_10_mb_limit(client, app):
    UserAccount.create("des@test.com", "password123", "designer", name="Dana")
    client.post("/login", data={"email": "des@test.com", "password": "password123"})
    assert b"Maximum 10 MB per photo" in client.get("/designer/portfolio/add").data


# --- PM-03 a new category needs a background image ---------------------------------

def test_category_cannot_be_created_without_a_background(app):
    with pytest.raises(ValueError, match="background image"):
        CreateCategoryController().create("Balcony")
    assert not IDPCategory.name_exists("Balcony")


def test_category_background_must_be_a_real_image(app):
    fake = FileStorage(io.BytesIO(b"not an image"), filename="bg.png")
    with pytest.raises(ValueError, match="not a valid JPG or PNG"):
        CreateCategoryController().create("Balcony", photo=fake)
    assert not IDPCategory.name_exists("Balcony")


def test_created_category_has_its_background_on_the_landing_page(client, app):
    category = CreateCategoryController().create("Balcony", photo=png_upload("balcony.png"))
    assert category.photo.filename == "balcony.png" and category.photo.content_type == "image/png"
    assert category.id in IDPCategory.photo_ids().values()
    response = client.get(f"/customer/categories/{category.id}/photo")
    assert response.status_code == 200 and response.data == png_bytes()


def test_create_form_asks_for_the_background(client, app):
    UserAccount.create("pm@test.com", "password123", "platform", name="Pat")
    client.post("/login", data={"email": "pm@test.com", "password": "password123"})
    page = client.get("/platform/categories/new").data.decode()
    assert 'enctype="multipart/form-data"' in page and 'type="file" name="photo"' in page
    assert b"background image" in client.post("/platform/categories/new", data={"name": "Balcony"}).data
    client.post("/platform/categories/new", data={"name": "Balcony", "photo": png_field()},
                content_type="multipart/form-data")
    assert IDPCategory.query.filter_by(name="Balcony").one().photo is not None


def test_editing_keeps_or_replaces_the_background(app):
    category = CreateCategoryController().create("Balcony", photo=png_upload("first.png"))
    UpdateCategoryController().update(category.id, "Balcony", "")
    assert category.photo.filename == "first.png"
    UpdateCategoryController().update(category.id, "Balcony", "", png_upload("second.png"))
    assert IDPCategory.get(category.id).photo.filename == "second.png"


# --- UA-17 the designer is told when a reported IDP is removed ---------------------

def reported_project():
    admin = UserAccount.create("admin@test.com", "password123", "admin")
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    other = UserAccount.create("des2@test.com", "password123", "designer", name="Other Des")
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    loft = IDP(title="Scandinavian Loft", category="Living Room", designer_id=designer.id)
    db.session.add(loft)
    db.session.commit()
    report = ReportIDPController().report(customer.id, loft.id, "Spam or advertising")
    return admin, designer, other, customer, loft, report


def test_removing_a_reported_idp_sends_the_designer_a_notice(app):
    admin, designer, other, customer, loft, report = reported_project()
    ReviewReportsController().remove_idp(report.id, admin.id, "Advertises another company")
    notice = Announcement.query.one()
    assert notice.recipient_id == designer.id and notice.is_personal and not notice.is_for_everyone
    assert "Scandinavian Loft" in notice.title
    assert "reported" in notice.message and "removed" in notice.message
    assert "Spam or advertising" in notice.message and "Advertises another company" in notice.message
    # Only that designer sees it, not other designers or other roles
    assert Announcement.latest(3, role="designer", user_id=designer.id) == [notice]
    assert Announcement.latest(3, role="designer", user_id=other.id) == []
    assert Announcement.latest(3, role="designer") == []
    assert Announcement.latest(3, role="customer", user_id=customer.id) == []


def test_dismissing_a_report_sends_no_notice(app):
    admin, *_, report = reported_project()
    ReviewReportsController().dismiss(report.id, admin.id)
    assert Announcement.query.count() == 0


def test_designer_sees_notice_and_project_removed_in_portfolio(client, app):
    admin, designer, other, customer, loft, report = reported_project()
    ReviewReportsController().remove_idp(report.id, admin.id, "Advertises another company")
    client.post("/login", data={"email": "des@test.com", "password": "password123"})
    assert "Project removed: Scandinavian Loft" in client.get("/designer/").data.decode()
    portfolio = client.get("/designer/portfolio").data.decode()
    assert "Project Removed" in portfolio


def test_admin_history_labels_the_personal_notice(client, app):
    admin, designer, other, customer, loft, report = reported_project()
    ReviewReportsController().remove_idp(report.id, admin.id, "Advertises another company")
    client.post("/login", data={"email": "admin@test.com", "password": "password123"})
    page = client.get("/admin/announcements").data.decode()
    assert "(personal notice)" in page
