"""Acceptance criteria from the User Stories sheet, Customer stories C-01 to C-17.
Each test names the criteria (AC) it checks and drives the real pages."""
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from PIL import Image

from app.entity.db import db
from app.entity.idp import IDP
from app.entity.idp_photo import IDPPhoto
from app.entity.user_account import UserAccount


def user(role, email, name=None, **kw):
    return UserAccount.create(email, "password123", role, name=name or role.title(), **kw)


def login(client, email, role=None, password="password123"):
    data = {"email": email, "password": password}
    if role:
        data["role"] = role
    return client.post("/login", data=data, follow_redirects=False)


def project(designer, title="Scandi Loft", category="Living Room", **kw):
    idp = IDP(title=title, category=category, designer_id=designer.id, is_current=True, **kw)
    db.session.add(idp)
    db.session.commit()
    return idp


@pytest.fixture
def world(client, app):
    designer = user("designer", "des@test.com", "Dana Ong")
    customer = user("customer", "cus@test.com", "Sarah Tan", phone="91234567")
    loft = project(designer, "Scandi Loft", "Living Room", description="Bright airy loft")
    kitchen = project(designer, "Teak Kitchen", "Kitchen", description="Warm teak")
    return designer, customer, loft, kitchen


def as_customer(client):
    login(client, "cus@test.com", "customer")


# C-01 ------------------------------------------------------------------------------------

def test_c01_registration_rules(client, app):
    form = {"first_name": "Amy", "last_name": "Lee", "email": "amy@test.com",
            "phone": "81234567", "password": "password123", "confirm_password": "password123"}
    page = client.get("/register").get_data(as_text=True)
    for field in ("first_name", "last_name", "email", "phone", "password"):  # AC1
        assert f'name="{field}"' in page
    assert client.post("/register", data=form).status_code == 302
    account = UserAccount.query.filter_by(email="amy@test.com").one()
    assert account.role == "customer"                                          # AC5
    assert login(client, "amy@test.com", "customer").status_code == 302
    dup = client.post("/register", data={**form, "phone": "81234568"})
    assert b"Email already registered" in dup.data                              # AC2
    short = client.post("/register", data={**form, "email": "b@test.com", "password": "short",
                                           "confirm_password": "short"})
    assert b"at least 8 characters" in short.data                               # AC3
    assert UserAccount.query.filter_by(email="b@test.com").count() == 0         # AC4
    assert b"valid email" in client.post("/register", data={**form, "email": "nope"}).data


# C-02 / C-03 -----------------------------------------------------------------------------

def test_c02_login_rules(client, world):
    assert login(client, "cus@test.com", "customer").status_code == 302         # AC2
    client.get("/logout")
    for email, password in (("cus@test.com", "wrongpass1"), ("nobody@test.com", "password123")):
        page = client.post("/login", data={"email": email, "password": password, "role": "customer"})
        assert b"Invalid email or password" in page.data                        # AC3
    UserAccount.query.filter_by(email="cus@test.com").one().set_suspended(True)
    page = client.post("/login", data={"email": "cus@test.com", "password": "password123", "role": "customer"})
    assert b"suspended" in page.data                                            # AC4
    assert client.get("/customer/favourites").status_code == 302                # AC5


def test_c03_logout_returns_to_login_and_pages_are_not_cached(client, world):
    as_customer(client)
    assert b"Log out" in client.get("/customer/favourites").data                # AC1
    cached = client.get("/customer/favourites")
    assert "no-store" in cached.headers.get("Cache-Control", "")                # AC3 (Back button)
    response = client.get("/logout")
    assert response.headers["Location"].endswith("/login")                      # AC2
    assert "/login" in client.get("/customer/favourites").headers["Location"]   # AC3


# C-04 / C-05 / C-17 ------------------------------------------------------------------------

def test_c04_search(client, world):
    designer, _, loft, kitchen = world
    page = client.get("/customer/?q=loft").get_data(as_text=True)
    assert "Scandi Loft" in page and "Teak Kitchen" not in page                 # AC1, AC2 (title)
    assert "airy" in client.get("/customer/?q=airy").get_data(as_text=True)     # AC2 (description)
    assert "LIVING ROOM" in page and "Dana Ong" in page                         # AC3 category, designer
    assert "No results found" in client.get("/customer/?q=zzzz").get_data(as_text=True)  # AC4
    designer.is_suspended = True
    db.session.commit()
    assert "Scandi Loft" not in client.get("/customer/").get_data(as_text=True)  # AC5


def test_c04_result_shows_a_thumbnail_when_the_project_has_photos(client, world):
    _, _, loft, _ = world
    buffer = BytesIO()
    Image.new("RGB", (4, 4)).save(buffer, "PNG")
    photo = IDPPhoto(idp_id=loft.id, filename="a.png", content_type="image/png", data=buffer.getvalue())
    db.session.add(photo)
    db.session.commit()
    assert f"/customer/photos/{photo.id}" in client.get("/customer/?q=loft").get_data(as_text=True)


def test_c05_filter_by_one_or_more_categories(client, world):
    both = client.get("/customer/?category=Kitchen&category=Living+Room").get_data(as_text=True)
    assert "Scandi Loft" in both and "Teak Kitchen" in both                     # AC1
    one = client.get("/customer/?category=Kitchen").get_data(as_text=True)
    assert "Teak Kitchen" in one and "Scandi Loft" not in one                   # AC2
    combined = client.get("/customer/?category=Kitchen&q=loft").get_data(as_text=True)
    assert "No results found" in combined                                       # AC3, AC5
    assert "Scandi Loft" in client.get("/customer/?category=").get_data(as_text=True)  # AC4


def test_c17_sort_newest_and_most_viewed_keeps_filters(client, world):
    designer, _, loft, kitchen = world
    loft.view_count, loft.created_at = 5, datetime.now() - timedelta(days=9)
    kitchen.view_count, kitchen.created_at = 50, datetime.now() - timedelta(days=1)
    db.session.commit()
    viewed = client.get("/customer/?sort=views").get_data(as_text=True)
    newest = client.get("/customer/?sort=newest").get_data(as_text=True)
    assert viewed.index("Teak Kitchen") < viewed.index("Scandi Loft")           # AC3
    kitchen.view_count, loft.view_count = 1, 99
    db.session.commit()
    assert client.get("/customer/?sort=views").get_data(as_text=True).index("Scandi Loft") < \
        client.get("/customer/?sort=views").get_data(as_text=True).index("Teak Kitchen")
    assert newest.index("Teak Kitchen") < newest.index("Scandi Loft")           # AC2
    kept = client.get("/customer/?sort=newest&q=kitchen&category=Kitchen").get_data(as_text=True)
    assert "Scandi Loft" not in kept and "Teak Kitchen" in kept                 # AC4


# C-06 ------------------------------------------------------------------------------------

def test_c06_view_idp(client, world):
    designer, _, loft, _ = world
    before = loft.view_count or 0
    page = client.get(f"/customer/projects/{loft.id}").get_data(as_text=True)
    for text in ("Scandi Loft", "Bright airy loft", "Living Room", "Current", "Dana Ong"):  # AC2
        assert text in page
    assert IDP.get(loft.id).view_count == before + 1                            # AC3
    IDP.get(loft.id).delete()
    gone = client.get(f"/customer/projects/{loft.id}")
    assert gone.status_code == 404 and b"Project not available" in gone.data     # AC4


# C-07 to C-10 ------------------------------------------------------------------------------

def test_c07_to_c10_favourites(client, world):
    _, _, loft, kitchen = world
    page = client.get(f"/customer/projects/{loft.id}").get_data(as_text=True)
    assert "Log in" in page                                                      # AC1 (guest)
    assert client.post(f"/customer/favourites/{loft.id}").status_code == 302     # AC1: must log in
    as_customer(client)
    assert "Save" in client.get(f"/customer/projects/{loft.id}").get_data(as_text=True)  # C-07 AC2
    saved = client.post(f"/customer/favourites/{loft.id}", follow_redirects=True).get_data(as_text=True)
    assert "Saved" in saved                                                      # C-07 AC3
    assert IDP.get(loft.id).shortlist_count == 1                                 # C-07 AC5
    client.post(f"/customer/favourites/{loft.id}")
    assert IDP.get(loft.id).shortlist_count == 1                                 # C-07 AC4
    listing = client.get("/customer/favourites").get_data(as_text=True)
    assert "Scandi Loft" in listing and "LIVING ROOM" in listing and "Dana Ong" in listing   # C-08 AC2
    assert f"/customer/projects/{loft.id}" in listing                            # C-08 AC3
    assert "Teak Kitchen" not in listing                                         # C-08 AC4 / C-09 AC3
    assert "Scandi Loft" in client.get("/customer/favourites?q=scandi").get_data(as_text=True)  # C-09 AC2
    assert "No results found" in client.get("/customer/favourites?q=zzz").get_data(as_text=True)  # C-09 AC4
    client.post(f"/customer/favourites/{loft.id}/remove")                        # C-10 AC1, AC2
    assert "You have no saved projects yet" in client.get("/customer/favourites").get_data(as_text=True)  # C-08 AC5
    assert IDP.get(loft.id).shortlist_count == 0                                 # C-10 AC3
    assert IDP.get(loft.id) is not None                                          # C-10 AC4
    client.post(f"/customer/favourites/{loft.id}")
    assert IDP.get(loft.id).shortlist_count == 1


# C-11 / C-12 / C-14 --------------------------------------------------------------------------

def test_c11_profile_shows_details_and_date_joined_but_never_the_password(client, world):
    as_customer(client)
    page = client.get("/customer/profile").get_data(as_text=True)
    assert "Sarah" in page and "cus@test.com" in page and "91234567" in page    # AC2
    assert datetime.now().strftime("%Y") in page and "Joined" in page           # AC2 date joined
    assert "password123" not in page and "pbkdf2" not in page and "scrypt" not in page  # AC3
    assert client.get("/customer/profile").status_code == 200
    assert "/login" in app_client_anonymous(client).get("/customer/profile").headers["Location"]  # AC1/AC4


def app_client_anonymous(client):
    return client.application.test_client()


def test_c12_update_profile(client, world):
    user("customer", "other@test.com", "Other", phone="81112222")
    as_customer(client)
    page = client.get("/customer/profile").get_data(as_text=True)
    assert 'value="Sarah"' in page and 'value="cus@test.com"' in page          # AC1 pre-filled
    base = {"first_name": "Sarah", "last_name": "Lim", "email": "cus@test.com", "phone": "91234567",
            "current_password": "password123"}
    ok = client.post("/customer/profile", data=base, follow_redirects=True).get_data(as_text=True)
    assert "Lim" in ok                                                           # AC2, AC5
    bad = client.post("/customer/profile", data={**base, "email": "nope"})
    assert b"valid email" in bad.data                                            # AC3
    taken = client.post("/customer/profile", data={**base, "email": "other@test.com"})
    assert b"already" in taken.data                                              # AC4
    assert UserAccount.query.filter_by(email="cus@test.com").count() == 1


def test_c14_change_password(client, world):
    as_customer(client)
    path = "/customer/profile/password"
    new = {"current_password": "password123", "new_password": "Newpass123", "confirm_password": "Newpass123"}
    wrong = client.post(path, data={**new, "current_password": "wrong"}, follow_redirects=True)
    assert b"current password is incorrect" in wrong.data                        # AC1, AC3
    mismatch = client.post(path, data={**new, "confirm_password": "different1"}, follow_redirects=True)
    assert b"do not match" in mismatch.data                                      # AC2, AC3
    weak = client.post(path, data={**new, "new_password": "short", "confirm_password": "short"}, follow_redirects=True)
    assert b"at least 8" in weak.data                                            # AC2
    client.post(path, data=new)
    client.get("/logout")
    assert b"Invalid email or password" in client.post(
        "/login", data={"email": "cus@test.com", "password": "password123", "role": "customer"}).data  # AC4


# C-13 ------------------------------------------------------------------------------------

def test_c13_designer_profile(client, world):
    designer, _, loft, _ = world
    page = client.get(f"/customer/designers/{designer.id}").get_data(as_text=True)
    assert "Dana Ong" in page and "des@test.com" in page or "Contact" in page   # AC2
    assert f"/customer/projects/{loft.id}" in page                               # AC3
    designer.is_suspended = True
    db.session.commit()
    assert client.get(f"/customer/designers/{designer.id}").status_code == 404   # AC4
    assert client.get(f"/customer/projects/{loft.id}").status_code == 404


# C-15 / C-16 ------------------------------------------------------------------------------

def test_c15_c16_report_and_enquiry(client, world):
    designer, customer, loft, _ = world
    as_customer(client)
    page = client.get(f"/customer/projects/{loft.id}").get_data(as_text=True)
    assert "Report" in page and "Send enquiry" in page                           # C-15 AC1, C-16 AC1
    assert "Send enquiry" in client.get(f"/customer/designers/{designer.id}").get_data(as_text=True)
    done = client.post(f"/customer/projects/{loft.id}/report", data={"reason": "Spam or advertising"},
                       follow_redirects=True)
    assert b"report" in done.data.lower()                                        # C-15 AC3
    empty = client.post(f"/customer/designers/{designer.id}/enquiry",
                        data={"name": "Sarah", "contact": "9123", "message": "  "}, follow_redirects=True)
    assert b"message" in empty.data.lower()                                      # C-16 AC2
    sent = client.post(f"/customer/designers/{designer.id}/enquiry",
                       data={"name": "Sarah", "contact": "91234567", "message": "Quote please", "idp_id": loft.id},
                       follow_redirects=True)
    assert b"enquiry has been sent" in sent.data                                 # C-16 AC3
