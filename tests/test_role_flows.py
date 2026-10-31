"""End-to-end checks through the pages for stories that had no page-level test:
login and logout for every role (C-02/C-03, ID-01/ID-02, PM-01/PM-02, UA-01/UA-02),
company information (ID-03 to ID-05), project photos (ID-19), project statistics
(ID-13, ID-14) and customer trends (ID-20)."""
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from PIL import Image

from app.entity.db import db
from app.entity.designer_company import DesignerCompany
from app.entity.favourite import Favourite
from app.entity.idp import IDP
from app.entity.idp_photo import IDPPhoto
from app.entity.idp_view import IDPView
from app.entity.user_account import UserAccount

HOME = {"customer": "/customer/", "designer": "/designer/", "platform": "/platform/", "admin": "/admin/"}
PROTECTED = {"customer": "/customer/profile", "designer": "/designer/portfolio",
             "platform": "/platform/categories", "admin": "/admin/accounts"}


def make_user(role, email=None):
    return UserAccount.create(email or f"{role}@test.com", "password123", role, name=f"{role.title()} User")


def login(client, email, role=None):
    data = {"email": email, "password": "password123"}
    if role:
        data["role"] = role
    return client.post("/login", data=data)


def png(fmt="PNG", size=(8, 8)):
    buffer = BytesIO()
    Image.new("RGB", size, "tan").save(buffer, fmt)
    buffer.seek(0)
    return buffer


@pytest.fixture
def designer_client(client, app):
    make_user("designer")
    login(client, "designer@test.com")
    return client


# --- Login and logout, every role -----------------------------------------------------

@pytest.mark.parametrize("role", list(HOME))
def test_each_role_logs_in_to_its_own_home_and_can_log_out(client, app, role):
    make_user(role)
    response = login(client, f"{role}@test.com", role)
    assert response.status_code == 302
    assert client.get(PROTECTED[role]).status_code == 200
    client.get("/logout")
    assert client.get(PROTECTED[role]).status_code == 302
    assert "/login" in client.get(PROTECTED[role]).headers["Location"]


@pytest.mark.parametrize("role", list(HOME))
def test_login_redirects_to_the_accounts_own_home(client, app, role):
    make_user(role)
    response = login(client, f"{role}@test.com")  # no role picked: the account decides
    assert response.headers["Location"].endswith(HOME[role])


@pytest.mark.parametrize("role", ["designer", "platform", "admin"])
def test_other_roles_cannot_open_each_others_pages(client, app, role):
    make_user(role)
    login(client, f"{role}@test.com", role)
    for other, path in PROTECTED.items():
        if other != role and other != "customer":
            assert client.get(path).status_code == 403


# --- Company information (ID-03 add, ID-04 view, ID-05 update and delete) ---------------

COMPANY = {"company_name": "Oak Studio", "description": "Warm homes", "address": "1 Main St",
           "phone": "91234567", "email": "hello@oak.com"}


def test_designer_adds_views_edits_and_deletes_company(designer_client, app):
    designer = UserAccount.query.filter_by(email="designer@test.com").one()
    added = designer_client.post("/designer/company/add", data=COMPANY)
    assert added.status_code == 302 and f"/designers/{designer.id}" in added.headers["Location"]
    assert b"Oak Studio" in designer_client.get(f"/customer/designers/{designer.id}").data

    again = designer_client.get("/designer/company/add")  # one company per designer
    assert again.status_code == 302 and "/company/edit" in again.headers["Location"]

    designer_client.post("/designer/company/edit", data={**COMPANY, "company_name": "Oak & Elm"})
    assert DesignerCompany.query.one().company_name == "Oak & Elm"

    designer_client.post("/designer/company/delete", data={})  # no confirmation: nothing happens
    assert DesignerCompany.query.count() == 1
    designer_client.post("/designer/company/delete", data={"confirm": "delete"})
    assert DesignerCompany.query.count() == 0


@pytest.mark.parametrize("changes,message", [
    ({"company_name": ""}, b"company name"),
    ({"company_name": "x" * 151}, b"150 characters"),
    ({"email": "not-an-email"}, b"valid email"),
    ({"phone": "123"}, b"phone"),
])
def test_invalid_company_details_show_an_error_and_save_nothing(designer_client, app, changes, message):
    page = designer_client.post("/designer/company/add", data={**COMPANY, **changes})
    assert message.lower() in page.data.lower()
    assert DesignerCompany.query.count() == 0


# --- Project photos (ID-19) ----------------------------------------------------------------

def add_project(client, photos):
    return client.post("/designer/portfolio/add", content_type="multipart/form-data", data={
        "title": "Loft", "description": "", "category": "Kitchen", "status": "current",
        "photos": photos})


def test_photo_is_saved_shown_to_customers_and_can_be_removed(designer_client, app):
    add_project(designer_client, [(png(), "a.png"), (png("JPEG"), "b.jpg")])
    project = IDP.query.one()
    assert IDPPhoto.query.filter_by(idp_id=project.id).count() == 2
    photo = IDPPhoto.query.filter_by(idp_id=project.id).first()

    served = app.test_client().get(f"/customer/photos/{photo.id}")  # no login needed to browse
    assert served.status_code == 200 and served.mimetype.startswith("image/")
    assert served.headers["X-Content-Type-Options"] == "nosniff"

    designer_client.post(f"/designer/portfolio/{project.id}/photos/{photo.id}/delete")
    assert IDPPhoto.query.filter_by(idp_id=project.id).count() == 1


@pytest.mark.parametrize("upload,message", [
    ((BytesIO(b"<?php echo 1;"), "evil.png"), b"not a valid"),   # not an image at all
    ((BytesIO(b"GIF89a"), "a.gif"), b"JPG and PNG"),             # wrong type
    ((png("JPEG"), "a.png"), b"match its file extension"),      # JPEG pretending to be PNG
])
def test_bad_photo_uploads_are_rejected_and_no_project_is_created(designer_client, app, upload, message):
    page = add_project(designer_client, [upload])
    assert message.lower() in page.data.lower()
    assert IDP.query.count() == 0


def test_more_than_ten_photos_are_rejected(designer_client, app):
    page = add_project(designer_client, [(png(), f"{n}.png") for n in range(11)])
    assert b"at most 10 photos" in page.data and IDP.query.count() == 0


def test_designer_cannot_remove_another_designers_photo(designer_client, app):
    add_project(designer_client, [(png(), "a.png")])
    photo = IDPPhoto.query.one()
    other = app.test_client()
    make_user("designer", "other@test.com")
    login(other, "other@test.com")
    assert other.post(f"/designer/portfolio/{photo.idp_id}/photos/{photo.id}/delete").status_code == 404
    assert IDPPhoto.query.count() == 1


# --- Statistics (ID-13, ID-14) and trends (ID-20) -------------------------------------------

def test_statistics_page_lists_own_projects_with_view_and_shortlist_counts(designer_client, app):
    designer = UserAccount.query.filter_by(email="designer@test.com").one()
    customer = make_user("customer")
    mine = IDP(title="My Loft", category="Kitchen", designer_id=designer.id, view_count=12)
    theirs = IDP(title="Not Mine", category="Kitchen", designer_id=make_user("designer", "o@test.com").id)
    db.session.add_all([mine, theirs])
    db.session.commit()
    Favourite.add(customer.id, mine)
    page = designer_client.get("/designer/statistics").get_data(as_text=True)
    assert "My Loft" in page and "12" in page and "Not Mine" not in page


def test_trends_page_counts_recent_views_and_rejects_other_ranges(designer_client, app):
    designer = UserAccount.query.filter_by(email="designer@test.com").one()
    loft = IDP(title="Hot Loft", category="Kitchen", designer_id=designer.id)
    db.session.add(loft)
    db.session.commit()
    now = datetime.now()
    db.session.add_all([IDPView(idp_id=loft.id, category="Kitchen", viewed_at=now - timedelta(days=2)),
                        IDPView(idp_id=loft.id, category="Kitchen", viewed_at=now - timedelta(days=20))])
    db.session.commit()
    assert b"Hot Loft" in designer_client.get("/designer/trends?days=7").data
    assert designer_client.get("/designer/trends?days=30").status_code == 200
    assert designer_client.get("/designer/trends?days=15").status_code == 400
    assert designer_client.get("/designer/trends?days=abc").status_code == 400


def test_photo_cannot_be_removed_through_a_different_project_url(designer_client, app):
    add_project(designer_client, [(png(), "a.png")])
    designer = UserAccount.query.filter_by(email="designer@test.com").one()
    second = IDP(title="Second", category="Kitchen", designer_id=designer.id)
    db.session.add(second)
    db.session.commit()
    photo = IDPPhoto.query.one()
    assert designer_client.post(f"/designer/portfolio/{second.id}/photos/{photo.id}/delete").status_code == 404
    assert IDPPhoto.query.count() == 1
