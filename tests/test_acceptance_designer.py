"""Acceptance criteria from the User Stories sheet, Interior Designer stories ID-01 to ID-21."""
from datetime import datetime, timedelta

import html

import pytest

from app.entity.db import db
from app.entity.designer_application import DesignerApplication
from app.entity.designer_company import DesignerCompany
from app.entity.enquiry import Enquiry
from app.entity.favourite import Favourite
from app.entity.idp import IDP
from app.entity.idp_view import IDPView
from app.entity.user_account import UserAccount

COMPANY = {"company_name": "Oak Studio", "description": "Warm homes", "address": "1 Main St",
           "phone": "91234567", "email": "hello@oak.com"}


def make(role, email, name=None, **kw):
    return UserAccount.create(email, "password123", role, name=name or role.title(), **kw)


def login(client, email, role="designer", password="password123"):
    return client.post("/login", data={"email": email, "password": password, "role": role})


@pytest.fixture
def dc(client, app):
    """A logged-in designer client."""
    make("designer", "des@test.com", "Dana Ong", phone="91234567")
    login(client, "des@test.com")
    return client


def text(response):
    return response.get_data(as_text=True)


# ID-01 / ID-02 ---------------------------------------------------------------------------

def test_id01_login_rules(client, app):
    make("designer", "des@test.com", "Dana")
    ok = login(client, "des@test.com")
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/designer/")  # AC2
    assert b"Welcome back" in client.get("/designer/").data
    client.get("/logout")
    assert b"Invalid email or password" in login(client, "des@test.com", password="nope12345").data  # AC3
    UserAccount.query.filter_by(email="des@test.com").one().set_suspended(True)
    assert b"suspended" in login(client, "des@test.com").data                        # AC4


def test_id01_pending_and_rejected_designers_cannot_log_in(client, app):
    """AC5: a designer whose registration is Pending or Rejected cannot use designer features."""
    for status, word in (("pending", b"being reviewed"), ("rejected", b"not approved")):
        application = DesignerApplication(
            name="Ann", email=f"{status}@test.com", phone="8123456" + str(len(status)),
            password_hash="x", company_name="Co", uen="12345678A", experience_years=1,
            status=status)
        db.session.add(application)
        db.session.commit()
        from werkzeug.security import generate_password_hash
        application.password_hash = generate_password_hash("password123")
        db.session.commit()
        page = client.post("/login", data={"email": f"{status}@test.com", "password": "password123"},
                           follow_redirects=True)
        assert word in page.data
        assert client.get("/designer/portfolio").status_code == 302


def test_id02_logout_is_on_every_page_and_returns_to_login(dc):
    for path in ("/designer/", "/designer/portfolio", "/designer/enquiries", "/designer/profile",
                 "/designer/company/add", "/designer/statistics", "/designer/trends", "/designer/portfolio/add"):
        assert "Log out" in text(dc.get(path, follow_redirects=True)), path        # AC1
    assert dc.get("/logout").headers["Location"].endswith("/login")                  # AC2
    assert "/login" in dc.get("/designer/portfolio").headers["Location"]             # AC3
    assert "/login" in dc.get("/designer/").headers["Location"]


# ID-03 / ID-04 / ID-05 company ---------------------------------------------------------------

def test_id03_to_id05_company(dc, app):
    designer = UserAccount.query.filter_by(email="des@test.com").one()
    empty = text(dc.get("/designer/company"))
    assert "Add company information" in empty or "add" in empty.lower()               # ID-04 AC3
    form = text(dc.get("/designer/company/add"))
    for field in ("company_name", "description", "address", "phone", "email"):         # ID-03 AC1/AC2
        assert f'name="{field}"' in form
    assert "company_name" in form and "required" in form
    assert b"company name" in dc.post("/designer/company/add", data={**COMPANY, "company_name": ""}).data.lower()
    assert DesignerCompany.query.count() == 0                                          # ID-03 AC3
    dc.post("/designer/company/add", data=COMPANY)
    assert "Oak Studio" in text(app.test_client().get(f"/customer/designers/{designer.id}"))  # ID-03 AC4
    assert "/company/edit" in dc.get("/designer/company/add").headers["Location"]       # ID-03 AC5
    assert "Oak Studio" in text(dc.get(f"/customer/designers/{designer.id}"))           # ID-04 AC2
    edit = text(dc.get("/designer/company/edit"))
    assert 'value="Oak Studio"' in edit and "1 Main St" in edit                         # ID-05 AC1
    dc.post("/designer/company/edit", data={**COMPANY, "company_name": "Oak & Elm"})
    assert "Oak &amp; Elm" in text(app.test_client().get(f"/customer/designers/{designer.id}"))  # AC2, AC4
    bad = dc.post("/designer/company/edit", data={**COMPANY, "email": "nope"})
    assert b"valid email" in bad.data and DesignerCompany.query.one().company_name == "Oak & Elm"  # AC3


def test_id04_id05_company_is_only_the_designers_own(dc, app):
    other = make("designer", "o@test.com", "Olly")
    DesignerCompany.create(account_id=other.id, company_name="Not Mine", description="", address="",
                           phone="", email="")
    assert "Not Mine" not in text(dc.get("/designer/company", follow_redirects=True))
    assert "Not Mine" not in text(dc.get("/designer/company/edit", follow_redirects=True))
    dc.post("/designer/company/edit", data={**COMPANY, "company_name": "Hijack"})
    assert DesignerCompany.query.filter_by(account_id=other.id).one().company_name == "Not Mine"


# ID-06 to ID-12 portfolio ----------------------------------------------------------------------

def add(client, **over):
    data = {"title": "Loft", "description": "d", "category": "Kitchen", "status": "current", **over}
    return client.post("/designer/portfolio/add", data=data, content_type="multipart/form-data")


def test_id06_add_idp(dc, app):
    assert "/login" in app.test_client().get("/designer/portfolio/add").headers["Location"]   # AC1
    form = text(dc.get("/designer/portfolio/add"))
    for field in ("title", "description", "category", "status"):                                # AC2
        assert f'name="{field}"' in form
    assert add(dc).status_code == 302                                                           # AC3
    assert b"title" in add(dc, title="").data.lower()                                           # AC4
    assert add(dc, category="Nope").status_code == 200 and IDP.query.count() == 1
    assert "Loft" in text(dc.get("/designer/portfolio"))                                        # AC5


def test_id07_id08_view_and_search_portfolio(dc, app):
    other = make("designer", "o@test.com", "Olly")
    add(dc, title="Teak Loft")
    add(dc, title="Oak Kitchen", category="Kitchen", status="past")
    db.session.add(IDP(title="Teak Other", category="Kitchen", designer_id=other.id))
    db.session.commit()
    page = text(dc.get("/designer/portfolio"))
    assert "Teak Loft" in page and "Oak Kitchen" in page and "Teak Other" not in page          # ID-07 AC2
    assert "Kitchen" in page and "Current" in page and "Past" in page                          # ID-07 AC3
    found = text(dc.get("/designer/portfolio?q=teak"))
    assert "Teak Loft" in found and "Oak Kitchen" not in found and "Teak Other" not in found   # ID-08 AC2/AC3
    assert "No results found" in text(dc.get("/designer/portfolio?q=zzzz"))                    # ID-08 AC4
    assert dc.get("/designer/portfolio/9999/edit").status_code == 404                           # ID-07 AC4


def test_id09_edit_idp(dc, app):
    other = make("designer", "o@test.com", "Olly")
    add(dc, title="Mine")
    mine = IDP.query.filter_by(title="Mine").one()
    theirs = IDP(title="Theirs", category="Kitchen", designer_id=other.id)
    db.session.add(theirs)
    db.session.commit()
    assert dc.get(f"/designer/portfolio/{theirs.id}/edit").status_code == 404                   # AC1
    assert 'value="Mine"' in text(dc.get(f"/designer/portfolio/{mine.id}/edit"))               # AC2
    dc.post(f"/designer/portfolio/{mine.id}/edit", data={
        "title": "Mine v2", "description": "d", "category": "Kitchen", "status": "current"},
        content_type="multipart/form-data")
    assert IDP.get(mine.id).title == "Mine v2"                                                  # AC3
    assert b"title" in dc.post(f"/designer/portfolio/{mine.id}/edit", data={
        "title": "", "description": "", "category": "Kitchen", "status": "current"},
        content_type="multipart/form-data").data.lower()                                        # AC4
    assert "Mine v2" in text(dc.get("/designer/portfolio"))                                     # AC5


def test_id10_delete_idp_asks_first_and_cancel_keeps_it(dc, app):
    other = make("designer", "o@test.com", "Olly")
    add(dc, title="Mine")
    mine = IDP.query.one()
    theirs = IDP(title="Theirs", category="Kitchen", designer_id=other.id)
    db.session.add(theirs)
    db.session.commit()
    assert dc.post(f"/designer/portfolio/{theirs.id}/delete").status_code == 404                # AC1
    ask = text(dc.get(f"/designer/portfolio/{mine.id}/delete/confirm"))
    assert "Mine" in ask and "Confirm" in ask and IDP.get(mine.id) is not None                  # AC2
    assert "Cancel" in ask                                                                      # AC4 (a way out)
    dc.post(f"/designer/portfolio/{mine.id}/delete", data={"confirm": "cancel"})
    assert IDP.get(mine.id) is not None                                                         # AC4
    dc.post(f"/designer/portfolio/{mine.id}/delete", data={"confirm": "delete"})
    assert IDP.get(mine.id) is None                                                             # AC3
    assert "Mine" not in text(dc.get("/designer/portfolio"))                                    # AC5


def test_id11_id12_status_and_category_reach_customers(dc, app):
    add(dc, title="Past Loft", category="Bedroom", status="past")
    idp = IDP.query.one()
    public = app.test_client()
    page = text(public.get(f"/customer/projects/{idp.id}"))
    assert "Past project" in page and "Bedroom" in page                                          # ID-11 AC3/4, ID-12
    dc.post(f"/designer/portfolio/{idp.id}/status", data={"status": "current"})
    assert "Current project" in text(public.get(f"/customer/projects/{idp.id}"))                # ID-11 AC1/AC2
    form = text(dc.get("/designer/portfolio/add"))
    for name in IDP.categories():
        assert f'value="{html.escape(name)}"' in form                                                        # ID-12 AC1/AC2
    assert 'value="Space"' not in form
    assert "Past Loft" in text(public.get("/customer/?category=Bedroom"))                       # ID-12 AC4
    assert "Past Loft" not in text(public.get("/customer/?category=Kitchen"))


# ID-13 / ID-14 ------------------------------------------------------------------------------------

def test_id13_id14_counts_follow_customer_actions(dc, app):
    customer = make("customer", "cus@test.com", "Sarah", phone="81112222")
    add(dc, title="One")
    add(dc, title="Two")
    one, two = IDP.query.filter_by(title="One").one(), IDP.query.filter_by(title="Two").one()
    visitor = app.test_client()
    visitor.get(f"/customer/projects/{one.id}")
    visitor.get(f"/customer/projects/{one.id}")
    visitor.get(f"/customer/projects/{two.id}")
    assert (IDP.get(one.id).view_count, IDP.get(two.id).view_count) == (2, 1)                    # ID-13 AC3/AC4
    Favourite.add(customer.id, IDP.get(one.id))
    stats = text(dc.get("/designer/statistics"))
    assert "One" in stats and "Two" in stats                                                     # AC1
    assert (IDP.get(one.id).shortlist_count, IDP.get(two.id).shortlist_count) == (1, 0)         # ID-14 AC2/AC4


# ID-15 / ID-16 registration and status --------------------------------------------------------------

APPLY = {"email": "ann@test.com", "phone": "81234567",
         "password": "password123", "confirm_password": "password123", "company_name": "Ann Studio",
         "uen": "201912345K", "experience_years": "5", "portfolio_url": "https://ann.example", "description": "x"}


def test_id15_registration_form(client, app):
    page = text(client.get("/register/designer"))
    for field in ("company_name", "email", "phone", "password", "confirm_password", "uen",
                  "experience_years", "portfolio_url", "description"):                           # AC1
        assert f'name="{field}"' in page
    assert 'name="first_name"' not in page and 'name="last_name"' not in page
    done = client.post("/register/designer", data=APPLY, follow_redirects=True)
    assert b"submitted successfully" in done.data and b"Pending" in done.data                    # AC2, AC5
    assert DesignerApplication.query.filter_by(email="ann@test.com").one().status == "pending"  # AC4
    assert b"company name" in client.post("/register/designer",
                                          data={**APPLY, "email": "b@test.com", "company_name": ""}).data.lower()  # AC3
    assert b"valid email" in client.post("/register/designer", data={**APPLY, "email": "nope"}).data


def test_id16_designer_sees_registration_status(client, app):
    attempt = {"email": "ann@test.com", "password": "password123"}
    page = client.post("/register/designer", data=APPLY, follow_redirects=True)
    assert b"Pending" in page.data and b"201912345K" in page.data                               # AC1/AC2 (card after applying)
    assert b"Invalid email or password" in client.post(
        "/login", data={**attempt, "password": "wrong-password"}, follow_redirects=True).data   # no card without the password
    application = DesignerApplication.query.one()
    admin = make("admin", "admin@test.com", "Ann")
    from app.control.review_designer_application_controller import ReviewDesignerApplicationController
    ReviewDesignerApplicationController().reject(application.id, admin.id, "Incomplete UEN")
    page = client.post("/login", data=attempt, follow_redirects=True)
    assert b"Rejected" in page.data and b"Incomplete UEN" in page.data
    assert client.get("/designer/").status_code == 302                                          # AC4
    application.status = "pending"
    db.session.commit()
    ReviewDesignerApplicationController().approve(application.id, admin.id)
    assert login(client, "ann@test.com").status_code == 302                                     # AC3
    assert b"Welcome back" in client.get("/designer/").data


# ID-17 / ID-18 --------------------------------------------------------------------------------------

def test_id17_profile_shows_details_and_status_never_the_password(dc, app):
    page = text(dc.get("/designer/profile"))
    assert "Dana" in page and "des@test.com" in page and "91234567" in page                      # AC2
    assert "Registration" in page and "approved" in page.lower()
    assert "password123" not in page and "pbkdf2" not in page and "scrypt" not in page           # AC3
    assert "/login" in app.test_client().get("/designer/profile").headers["Location"]            # AC1/AC4


def test_id18_edit_profile(dc, app):
    make("designer", "o@test.com", "Olly", phone="82223333")
    page = text(dc.get("/designer/profile"))
    assert 'value="des@test.com"' in page                                                        # AC1
    base = {"company_name": "Dana Studio", "email": "des@test.com", "phone": "91234567",
            "current_password": "password123"}
    assert "Profile updated" in text(dc.post("/designer/profile", data=base, follow_redirects=True))  # AC2, AC5
    assert b"valid email" in dc.post("/designer/profile", data={**base, "email": "nope"}).data   # AC3
    assert b"already" in dc.post("/designer/profile", data={**base, "email": "o@test.com"}).data  # AC4


# ID-20 / ID-21 -----------------------------------------------------------------------------------------

def test_id20_trends_across_the_platform_filter_and_empty_message(dc, app):
    other = make("designer", "o@test.com", "Olly")
    theirs = IDP(title="Rival Loft", category="Bedroom", designer_id=other.id)
    db.session.add(theirs)
    db.session.commit()
    assert "No trend data" in text(dc.get("/designer/trends"))                                     # AC5
    now = datetime.now()
    db.session.add_all([IDPView(idp_id=theirs.id, category="Bedroom", viewed_at=now - timedelta(days=3)),
                        IDPView(idp_id=theirs.id, category="Bedroom", viewed_at=now - timedelta(days=20))])
    db.session.commit()
    week = text(dc.get("/designer/trends?days=7"))
    assert "Rival Loft" in week and "Bedroom" in week                                              # AC2 (other designers' too)
    assert "Last 7 days" in week and "Last 30 days" in week                                        # AC3
    month = text(dc.get("/designer/trends?days=30"))
    assert "<td>2</td>" in month and "<td>1</td>" in week                                          # AC4 matches views


def test_id21_enquiry_list_newest_first_with_details(dc, app):
    designer = UserAccount.query.filter_by(email="des@test.com").one()
    other = make("designer", "o@test.com", "Olly")
    cus = make("customer", "cus@test.com", "Sarah", phone="81112222")
    loft = IDP(title="Loft", category="Kitchen", designer_id=designer.id)
    db.session.add(loft)
    db.session.commit()
    old = Enquiry(customer_id=cus.id, designer_id=designer.id, idp_id=loft.id, name="Old Ann", contact="a", message="first msg",
                  created_at=datetime.now() - timedelta(days=2))
    new = Enquiry(customer_id=cus.id, designer_id=designer.id, idp_id=None, name="New Bob", contact="b", message="second msg")
    mine_not = Enquiry(customer_id=cus.id, designer_id=other.id, name="Zed", contact="z", message="not yours")
    db.session.add_all([old, new, mine_not])
    db.session.commit()
    page = text(dc.get("/designer/enquiries"))
    assert page.index("New Bob") < page.index("Old Ann")                                           # AC1
    assert "Loft" in page and "first msg" in page and "Old Ann" in page                            # AC2
    assert "Zed" not in page                                                                       # AC4


def test_id21_designer_can_reply_and_customer_sees_it(dc, app):
    designer = UserAccount.query.filter_by(email="des@test.com").one()
    cus = make("customer", "cus@test.com", "Sarah", phone="81112222")
    enquiry = Enquiry(customer_id=cus.id, designer_id=designer.id, name="Ann", contact="a", message="hello")
    db.session.add(enquiry)
    db.session.commit()
    assert b"Reply" in dc.get("/designer/enquiries").data
    dc.post(f"/designer/enquiries/{enquiry.id}/reply", data={"message": "Happy to help, Ann!"})          # AC3
    cc = dc.application.test_client()
    cc.post("/login", data={"email": "cus@test.com", "password": "password123", "role": "customer"})
    assert "Happy to help, Ann!" in cc.get("/customer/enquiries").get_data(as_text=True)               # AC5


# Company profile picture and background ---------------------------------------------------------

def _image(colour):
    from io import BytesIO
    from PIL import Image
    out = BytesIO()
    Image.new("RGB", (40, 20), colour).save(out, "PNG")
    out.seek(0)
    return out


def test_company_profile_picture_and_background(dc, app):
    designer = UserAccount.query.filter_by(email="des@test.com").one()
    form = text(dc.get("/designer/company/add"))
    assert 'name="profile_photo"' in form and 'name="cover_photo"' in form
    dc.post("/designer/company/add", content_type="multipart/form-data",
            data={**COMPANY, "profile_photo": (_image("red"), "logo.png"),
                  "cover_photo": (_image("blue"), "banner.png")})
    company = DesignerCompany.query.one()
    assert company.profile_photo and company.cover_photo

    visitor = app.test_client()
    public = text(visitor.get(f"/customer/designers/{designer.id}"))
    assert f"/customer/designers/{designer.id}/company-cover" in public
    assert f"/customer/designers/{designer.id}/company-photo" in public
    assert visitor.get(f"/customer/designers/{designer.id}/company-cover").status_code == 200

    # Replace the background, then remove it
    dc.post("/designer/company/edit", content_type="multipart/form-data",
            data={**COMPANY, "cover_photo": (_image("green"), "new.png")})
    assert DesignerCompany.query.one().cover_photo.filename.startswith("new")
    dc.post("/designer/company/edit", data={**COMPANY, "remove_cover_photo": "1"})
    assert DesignerCompany.query.one().cover_photo is None
    assert DesignerCompany.query.one().profile_photo is not None
    assert visitor.get(f"/customer/designers/{designer.id}/company-cover").status_code == 404

    bad = dc.post("/designer/company/edit", content_type="multipart/form-data",
                  data={**COMPANY, "cover_photo": (_image("red"), "banner.gif")})
    assert b"Only JPG and PNG" in bad.data


def test_project_gallery_layout(dc, app):
    from app.entity.idp_photo import IDPPhoto
    add(dc, title="Gallery")
    idp = IDP.query.filter_by(title="Gallery").one()
    visitor = app.test_client()
    assert "No photos yet" in text(visitor.get(f"/customer/projects/{idp.id}"))
    for n in range(12):
        db.session.add(IDPPhoto(idp_id=idp.id, filename=f"p{n}.jpg", content_type="image/jpeg", data=b"x"))
    db.session.commit()
    page = text(visitor.get(f"/customer/projects/{idp.id}"))
    assert "1 / 12 photos" in page and "+7 more" in page          # 1 large + 4 beside it, 7 left over
    import re
    assert len(re.findall(r"data-lightbox[\s>]", page)) == 12      # every photo opens in the viewer


def test_designer_picture_shows_on_designer_cards_and_dashboard(dc, app):
    designer = UserAccount.query.filter_by(email="des@test.com").one()
    dc.post("/designer/company/add", content_type="multipart/form-data",
            data={**COMPANY, "profile_photo": (_image("red"), "logo.png")})
    add(dc, title="Loft")
    photo_url = f"/customer/designers/{designer.id}/company-photo"
    assert photo_url in text(app.test_client().get("/customer/designers"))
    assert photo_url in text(dc.get("/designer/"))
    assert "Your public profile" not in text(dc.get("/designer/profile"))
