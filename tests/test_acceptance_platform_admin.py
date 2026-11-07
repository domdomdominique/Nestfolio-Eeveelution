"""Acceptance criteria from the User Stories sheet, Platform Management (PM-01 to PM-11)
and User Admin (UA-01 to UA-18)."""
import html
import io
from datetime import date, datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app.control.send_announcement_controller import SendAnnouncementController
from app.entity.db import db
from app.entity.designer_application import DesignerApplication
from app.entity.favourite import Favourite
from app.entity.idp import IDP
from app.entity.idp_category import IDPCategory
from app.entity.idp_view import IDPView
from app.entity.report import Report
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile
from openpyxl import load_workbook

from conftest import png_field


def make(role, email, name=None, **kw):
    return UserAccount.create(email, "password123", role, name=name or role.title(), **kw)


def login(client, email, role, password="password123"):
    return client.post("/login", data={"email": email, "password": password, "role": role})


def text(response):
    return response.get_data(as_text=True)


@pytest.fixture
def pm(client, app):
    make("platform", "pm@test.com", "Pat Lim")
    login(client, "pm@test.com", "platform")
    return client


@pytest.fixture
def ua(client, app):
    make("admin", "admin@test.com", "Ann Admin")
    login(client, "admin@test.com", "admin")
    return client


# PM-01 / PM-02 / UA-01 / UA-02 -----------------------------------------------------------------

@pytest.mark.parametrize("role,home,other_pages", [
    ("platform", "/platform/", ["/admin/", "/designer/", "/customer/profile"]),
    ("admin", "/admin/", ["/platform/", "/designer/", "/customer/profile"]),
])
def test_login_logout_rules_for_platform_and_admin(client, app, role, home, other_pages):
    make(role, f"{role}@test.com", "Pat")
    ok = login(client, f"{role}@test.com", role)
    assert ok.status_code == 302 and ok.headers["Location"].endswith(home)               # AC2
    assert b"Log out" in client.get(home).data                                            # logout AC1
    for path in other_pages:                                                              # AC5
        assert client.get(path).status_code == 403
    out = client.get("/logout")                                                           # logout AC2
    assert out.headers["Location"].endswith("/login")
    assert "/login" in client.get(home).headers["Location"]                               # logout AC3
    assert b"Invalid email or password" in login(client, f"{role}@test.com", role, "wrongpass1").data  # AC3
    UserAccount.query.filter_by(email=f"{role}@test.com").one().set_suspended(True)
    assert b"suspended" in login(client, f"{role}@test.com", role).data                  # AC4


@pytest.mark.parametrize("role,page", [("platform", "/platform/categories"), ("admin", "/admin/accounts")])
def test_back_button_cannot_show_a_page_after_logout(client, app, role, page):
    make(role, f"{role}@test.com", "Pat")
    login(client, f"{role}@test.com", role)
    assert "no-store" in client.get(page).headers["Cache-Control"]


# PM-03 to PM-07 ----------------------------------------------------------------------------------

def test_pm03_create_category(pm, app):
    form = text(pm.get("/platform/categories/new"))
    assert 'name="name"' in form and 'name="description"' in form and "required" in form      # AC1, AC2
    assert b"category name" in pm.post("/platform/categories/new", data={"name": " "}).data.lower()
    pm.post("/platform/categories/new", data={"name": "Balcony", "photo": png_field()})        # description optional
    assert "Balcony" in text(pm.get("/platform/categories"))                                   # AC4
    assert b"already exists" in pm.post("/platform/categories/new", data={"name": "balcony", "photo": png_field()}).data   # AC3
    assert IDPCategory.query.filter(IDPCategory.name.ilike("balcony")).count() == 1
    make("designer", "des@test.com", "Dana")
    designer = app.test_client()
    login(designer, "des@test.com", "designer")
    assert 'value="Balcony"' in text(designer.get("/designer/portfolio/add"))                  # AC5 (ID-12)
    assert "Balcony" in text(app.test_client().get("/customer/"))                              # AC5 (C-05)


def test_pm04_view_categories_and_open_one(pm, app):
    designer = make("designer", "des@test.com", "Dana")
    db.session.add_all([IDP(title="A", category="Kitchen", designer_id=designer.id),
                        IDP(title="B", category="Kitchen", designer_id=designer.id)])
    db.session.commit()
    page = text(pm.get("/platform/categories"))
    assert "Kitchen" in page and "Kitchens and dining areas." in page                          # AC2
    row = page[page.index("Kitchen</strong>"):]
    assert ">2<" in row[:400]                                                                  # AC2 (IDP count)
    category = IDPCategory.query.filter_by(name="Kitchen").one()
    detail = pm.get(f"/platform/categories/{category.id}")                                     # AC3
    assert detail.status_code == 200 and "Kitchens and dining areas." in text(detail)
    IDPCategory.query.delete()
    db.session.commit()
    assert "No categories yet" in text(pm.get("/platform/categories"))                         # AC4


def test_pm05_update_category(pm, app):
    designer = make("designer", "des@test.com", "Dana")
    db.session.add(IDP(title="A", category="Kitchen", designer_id=designer.id))
    db.session.commit()
    kitchen = IDPCategory.query.filter_by(name="Kitchen").one()
    form = text(pm.get(f"/platform/categories/{kitchen.id}/edit"))
    assert 'value="Kitchen"' in form                                                           # AC1
    assert b"category name" in pm.post(f"/platform/categories/{kitchen.id}/edit", data={"name": ""}).data.lower()
    assert b"already exists" in pm.post(f"/platform/categories/{kitchen.id}/edit", data={"name": "Bedroom"}).data  # AC3
    pm.post(f"/platform/categories/{kitchen.id}/edit", data={"name": "Cookery", "description": "x"})
    assert IDP.query.one().category == "Cookery"                                               # AC4
    assert "A" in text(app.test_client().get("/customer/?category=Cookery"))


def test_pm06_delete_category(pm, app):
    designer = make("designer", "des@test.com", "Dana")
    db.session.add_all([IDP(title="A", category="Kitchen", designer_id=designer.id),
                        IDP(title="B", category="Kitchen", designer_id=designer.id)])
    db.session.commit()
    page = text(pm.get("/platform/categories"))
    assert "delete-dialog" in page and "Cancel" in page                                        # AC1/AC2
    kitchen = IDPCategory.query.filter_by(name="Kitchen").one()
    blocked = text(pm.post(f"/platform/categories/{kitchen.id}/delete", follow_redirects=True))
    assert "2 IDPs still use it" in blocked and IDPCategory.get(kitchen.id) is not None        # AC3
    spare = IDPCategory.query.filter_by(name="Bathroom").one()
    pm.post(f"/platform/categories/{spare.id}/delete")                                         # AC2
    assert IDPCategory.get(spare.id) is None
    assert "Bathroom" not in text(app.test_client().get("/customer/"))                         # AC4
    assert "Bathroom" not in IDP.categories()


def test_pm07_search_category(pm, app):
    assert "Kitchen" in text(pm.get("/platform/categories?q=kit"))                             # AC1/AC2
    assert "Bedroom" not in text(pm.get("/platform/categories?q=kit"))
    assert "No results found" in text(pm.get("/platform/categories?q=zzzz"))                   # AC3


# PM-08 to PM-11 ----------------------------------------------------------------------------------

DAY = date(2026, 10, 13)


def activity():
    designer = make("designer", "des@test.com", "Dana")
    customer = make("customer", "cus@test.com", "Sarah", phone="81112222")
    for account in (designer, customer):
        account.created_at = datetime(2026, 10, 13, 9)
    loft = IDP(title="Scandi Loft", category="Living Room", designer_id=designer.id,
               created_at=datetime(2026, 10, 13, 9))
    kitchen = IDP(title="Teak Kitchen", category="Kitchen", designer_id=designer.id,
                  created_at=datetime(2026, 10, 9, 9))
    db.session.add_all([loft, kitchen])
    db.session.commit()
    for idp, when in ((loft, DAY), (loft, DAY), (kitchen, DAY), (loft, date(2026, 10, 15)), (loft, date(2026, 11, 2))):
        db.session.add(IDPView(idp_id=idp.id, category=idp.category, viewed_at=datetime.combine(when, datetime.min.time()) + timedelta(hours=12)))
    Favourite.add(customer.id, loft)
    Favourite.find(customer.id, loft.id).saved_at = datetime(2026, 10, 13, 10)
    db.session.commit()


def figures(page):
    return {label: int(value) for label, value in
            __import__("re").findall(r'stat-label">([^<]+)</span><span class="stat-value">([\d,]+)', page)}


def test_pm08_to_pm10_reports(pm, app):
    activity()
    daily = text(pm.get("/platform/reports?kind=daily&value=2026-10-13"))
    assert figures(daily) == {"New user accounts": 2, "New IDPs": 1, "Total IDP views": 3, "Total shortlists": 1,
                             "New enquiries": 0}  # PM-08 AC2/AC4
    assert "Most viewed IDPs" in daily and "Most shortlisted categories" in daily               # PM-08 AC3
    assert "Scandi Loft" in daily
    empty = figures(text(pm.get("/platform/reports?kind=daily&value=2026-01-01")))
    assert set(empty.values()) == {0}                                                           # PM-08 AC5
    weekly = figures(text(pm.get("/platform/reports?kind=weekly&value=2026-10-14")))            # Mon 12 to Sun 18
    assert weekly["Total IDP views"] == 4 and weekly["New IDPs"] == 1                            # PM-09 AC2/AC4
    monthly = figures(text(pm.get("/platform/reports?kind=monthly&value=2026-10")))
    assert monthly["Total IDP views"] == 4 and monthly["New IDPs"] == 2                          # PM-10 AC2/AC4
    assert "Monthly report: October 2026" in text(pm.get("/platform/reports?kind=monthly&value=2026-10"))
    assert "valid date" in text(pm.get("/platform/reports?kind=daily&value=bad"))


def test_pm11_download_matches_the_screen_and_names_the_file(pm, app):
    activity()
    screen = figures(text(pm.get("/platform/reports?kind=daily&value=2026-10-13")))
    page = text(pm.get("/platform/reports?kind=daily&value=2026-10-13"))
    assert "format=pdf" in page and "format=xlsx" in page                                        # AC1/AC2
    xlsx = pm.get("/platform/reports/download?kind=daily&value=2026-10-13&format=xlsx")
    assert "daily_report_2026-10-13.xlsx" in xlsx.headers["Content-Disposition"]                 # AC4
    summary = load_workbook(io.BytesIO(xlsx.data))["Summary"].iter_rows(min_row=5, values_only=True)
    in_file = {row[0]: row[1] for row in summary if row[0]}
    assert {k: in_file[k] for k in screen} == screen                                             # AC3
    pdf = pm.get("/platform/reports/download?kind=weekly&value=2026-10-13&format=pdf")
    assert pdf.data.startswith(b"%PDF") and "weekly_report_2026-10-12.pdf" in pdf.headers["Content-Disposition"]
    assert "monthly_report_2026-10.xlsx" in pm.get(
        "/platform/reports/download?kind=monthly&value=2026-10&format=xlsx").headers["Content-Disposition"]


# UA-03 to UA-07 ----------------------------------------------------------------------------------

def new_account(client, **over):
    data = {"name": "New User", "email": "new@test.com", "phone": "91234567", "password": "password123",
            "profile": "customer", **over}
    return client.post("/admin/accounts/new", data=data)


def test_ua03_create_account(ua, app):
    form = text(ua.get("/admin/accounts/new"))
    for field in ("name", "email", "phone", "password", "profile"):                            # AC1
        assert f'name="{field}"' in form
    suspended = UserProfile.by_key("platform")
    suspended.status = "suspended"
    db.session.commit()
    assert 'value="platform"' in form                                                          # active: listed
    form = text(ua.get("/admin/accounts/new"))
    assert 'value="customer"' in form and 'value="platform"' not in form                       # AC2 active only
    assert b"suspended" in new_account(ua, profile="platform").data                            # AC2 (forged)
    assert new_account(ua).status_code == 302
    assert b"already registered" in new_account(ua, phone="82223333").data                     # AC3
    assert b"valid email" in new_account(ua, email="bad").data and b"phone" in new_account(ua, email="x@test.com", phone="1").data.lower()  # AC4
    account = UserAccount.query.filter_by(email="new@test.com").one()
    assert account.status == "Active"                                                          # AC5
    user = app.test_client()
    assert login(user, "new@test.com", "customer").status_code == 302


def test_ua04_view_account_never_shows_password(ua, app):
    new_account(ua)
    account = UserAccount.query.filter_by(email="new@test.com").one()
    assert f"/admin/accounts/{account.id}" in text(ua.get("/admin/accounts"))                  # AC1
    page = text(ua.get(f"/admin/accounts/{account.id}"))
    for value in ("New User", "new@test.com", "91234567", "Customer", "Active", str(date.today().year)):  # AC2
        assert value in page
    assert "password123" not in page and "pbkdf2" not in page and "scrypt" not in page         # AC3


def test_ua05_update_account(ua, app):
    make("customer", "other@test.com", "Other", phone="82223333")
    new_account(ua)
    account = UserAccount.query.filter_by(email="new@test.com").one()
    form = text(ua.get(f"/admin/accounts/{account.id}/edit"))
    assert 'value="New User"' in form and 'value="new@test.com"' in form                       # AC1
    data = {"name": "Renamed", "email": "new@test.com", "phone": "91234567", "profile": "designer"}
    ua.post(f"/admin/accounts/{account.id}/edit", data=data)
    view = text(ua.get(f"/admin/accounts/{account.id}"))
    assert "Renamed" in view and "Interior Designer" in view                                    # AC2, AC5
    assert b"already registered" in ua.post(f"/admin/accounts/{account.id}/edit",
                                            data={**data, "email": "other@test.com"}).data      # AC3
    assert b"valid email" in ua.post(f"/admin/accounts/{account.id}/edit", data={**data, "email": ""}).data  # AC4
    assert UserAccount.get(account.id).name == "Renamed"


def test_ua06_suspend_account(ua, app):
    new_account(ua)
    account = UserAccount.query.filter_by(email="new@test.com").one()
    page = text(ua.get(f"/admin/accounts/{account.id}"))
    assert "suspend-dialog" in page and "Cancel" in page                                        # AC1/AC2
    assert UserAccount.get(account.id).status == "Active"                                      # cancelled = unchanged
    ua.post(f"/admin/accounts/{account.id}/suspend")
    assert UserAccount.get(account.id).status == "Suspended"                                   # AC2
    assert b"suspended" in login(app.test_client(), "new@test.com", "customer").data           # AC3
    assert UserAccount.get(account.id).email == "new@test.com"                                 # AC4
    me = UserAccount.query.filter_by(email="admin@test.com").one()
    assert "Suspend account" not in text(ua.get(f"/admin/accounts/{me.id}"))                  # AC5
    ua.post(f"/admin/accounts/{me.id}/suspend")
    assert UserAccount.get(me.id).status == "Active"


def test_ua07_search_accounts(ua, app):
    make("customer", "amy@test.com", "Amy Tan", phone="81110000")
    make("designer", "bob@test.com", "Bob Lee", phone="82220000")
    make("customer", "cy@test.com", "Cy Wong", phone="83330000").set_suspended(True)
    by_name = text(ua.get("/admin/accounts?q=amy"))
    assert "Amy Tan" in by_name and "amy@test.com" in by_name and "Customer" in by_name and "Active" in by_name  # AC1/AC2
    assert "Bob Lee" in text(ua.get("/admin/accounts?q=bob@test"))
    only_designers = text(ua.get("/admin/accounts?profile=designer"))
    assert "Bob Lee" in only_designers and "Amy Tan" not in only_designers                      # AC3
    only_suspended = text(ua.get("/admin/accounts?status=suspended"))
    assert "Cy Wong" in only_suspended and "Amy Tan" not in only_suspended
    assert "No results found" in text(ua.get("/admin/accounts?q=zzzz"))                         # AC4


# UA-08 to UA-12 ----------------------------------------------------------------------------------

def test_ua08_create_profile(ua, app):
    form = text(ua.get("/admin/profiles/new"))
    assert 'name="name"' in form and 'name="description"' in form                              # AC1
    assert b"profile name" in ua.post("/admin/profiles/new", data={"name": ""}).data.lower()    # AC2/AC3
    ua.post("/admin/profiles/new", data={"name": "Moderator", "description": "Checks posts"})
    assert b"already exists" in ua.post("/admin/profiles/new", data={"name": "moderator"}).data  # AC2/AC3
    assert UserProfile.query.filter_by(name="Moderator").one().status == "active"               # AC4
    assert "Moderator" in text(ua.get("/admin/accounts/new"))                                    # AC4


def test_ua09_view_profiles_and_open_one(ua, app):
    page = text(ua.get("/admin/profiles"))
    assert "Customer" in page and "Browses, saves and enquires about IDPs." in page and "Active" in page   # AC2
    profile = UserProfile.by_key("customer")
    detail = ua.get(f"/admin/profiles/{profile.id}")                                            # AC3
    assert detail.status_code == 200 and "Browses, saves and enquires" in text(detail)


def test_ua10_update_profile(ua, app):
    make("customer", "cus@test.com", "Sarah", phone="81112222")
    profile = UserProfile.by_key("customer")
    assert 'value="Customer"' in text(ua.get(f"/admin/profiles/{profile.id}/edit"))             # AC1
    assert b"profile name" in ua.post(f"/admin/profiles/{profile.id}/edit", data={"name": ""}).data.lower()  # AC3
    assert b"already exists" in ua.post(f"/admin/profiles/{profile.id}/edit", data={"name": "Interior Designer"}).data
    ua.post(f"/admin/profiles/{profile.id}/edit", data={"name": "Homeowner", "description": ""})  # AC2
    account = UserAccount.query.filter_by(email="cus@test.com").one()
    assert "Homeowner" in text(ua.get(f"/admin/accounts/{account.id}"))                          # AC4


def test_ua11_suspend_profile(ua, app):
    cus = make("customer", "cus@test.com", "Sarah", phone="81112222")
    customer = UserProfile.by_key("customer")
    assert "suspend-dialog" in text(ua.get("/admin/profiles"))                                   # AC1
    assert customer.status == "active"
    ua.post(f"/admin/profiles/{customer.id}/suspend")
    assert UserProfile.get(customer.id).status == "suspended"                                    # AC2
    assert b"suspended" in login(app.test_client(), "cus@test.com", "customer").data             # AC3
    assert b"suspended" in new_account(ua, profile="customer").data                              # AC4
    admin_profile = UserProfile.by_key("admin")
    ua.post(f"/admin/profiles/{admin_profile.id}/suspend")
    assert UserProfile.get(admin_profile.id).status == "active"                                  # AC5
    assert "Suspend" not in text(ua.get("/admin/profiles")).split("User Admin")[1].split("</tr>")[0]


def test_ua12_search_profiles(ua, app):
    found = text(ua.get("/admin/profiles?q=cust"))
    assert "Customer" in found and "Active" in found and "Interior Designer" not in found        # AC1/AC2
    assert "No results found" in text(ua.get("/admin/profiles?q=zzzz"))                          # AC3


# UA-13 -------------------------------------------------------------------------------------------

def test_ua13_reactivate(ua, app):
    new_account(ua)
    account = UserAccount.query.filter_by(email="new@test.com").one()
    assert "Reactivate" not in text(ua.get(f"/admin/accounts/{account.id}"))                     # AC1
    ua.post(f"/admin/accounts/{account.id}/suspend")
    page = text(ua.get(f"/admin/accounts/{account.id}"))
    assert "Reactivate" in page and "reactivate-dialog" in page and "Cancel" in page             # AC1/AC2
    ua.post(f"/admin/accounts/{account.id}/reactivate")
    assert UserAccount.get(account.id).status == "Active"                                        # AC3
    assert login(app.test_client(), "new@test.com", "customer").status_code == 302               # AC4


# UA-14 / UA-15 -----------------------------------------------------------------------------------

def application(email="ann@test.com", status="pending"):
    a = DesignerApplication(name="Ann Lim", email=email, phone="8" + str(abs(hash(email)))[:7],
                            password_hash=generate_password_hash("password123"), company_name="Ann Studio",
                            uen="201912345K", experience_years=5, description="Cosy", status=status)
    db.session.add(a)
    db.session.commit()
    return a


def test_ua14_ua15_review_registrations(ua, app):
    approve_me, reject_me = application("a@test.com"), application("r@test.com")
    approved_already = application("old@test.com", "approved")
    pending = text(ua.get("/admin/applications"))
    assert "a@test.com" in pending and "r@test.com" in pending and "old@test.com" not in pending   # UA-14 AC1
    detail = text(ua.get(f"/admin/applications/{approve_me.id}"))
    assert "Ann Studio" in detail and "201912345K" in detail and "Cosy" in detail                  # UA-14 AC2
    assert "Reason" in text(ua.get(f"/admin/applications/{reject_me.id}"))                          # UA-15 AC1/AC2
    ua.post(f"/admin/applications/{approve_me.id}/approve", follow_redirects=True)  # follow: shows the flash once
    assert "a@test.com" not in text(ua.get("/admin/applications"))                                   # UA-14 AC3
    assert db.session.get(DesignerApplication, approve_me.id).status == "approved"
    ok = login(app.test_client(), "a@test.com", "designer")
    assert ok.status_code == 302                                                                     # UA-14 AC4
    ua.post(f"/admin/applications/{reject_me.id}/reject", data={"reason": "Incomplete portfolio"}, follow_redirects=True)
    assert "r@test.com" not in text(ua.get("/admin/applications"))                                   # UA-15 AC3
    rejected = db.session.get(DesignerApplication, reject_me.id)
    assert rejected.status == "rejected" and rejected.rejection_reason == "Incomplete portfolio"
    status = app.test_client().post("/login", data={"email": "r@test.com", "password": "password123"},
                                    follow_redirects=True)
    assert b"Rejected" in status.data and b"Incomplete portfolio" in status.data                    # UA-15 AC4
    assert login(app.test_client(), "r@test.com", "designer").headers["Location"].endswith("/registration-status")  # cannot use features; sees status card


# UA-16 / UA-17 / UA-18 ---------------------------------------------------------------------------

def test_ua16_reset_password(ua, app):
    new_account(ua)
    account = UserAccount.query.filter_by(email="new@test.com").one()
    page = text(ua.post(f"/admin/accounts/{account.id}/reset-password"))                            # AC1
    temp = page.split("<code")[1].split(">")[1].split("<")[0].strip()                              # AC2
    assert len(temp) >= 8 and "Temporary password" in page
    assert "Temporary password" not in text(ua.get(f"/admin/accounts/{account.id}"))                # shown once
    other = app.test_client()
    assert b"Invalid email or password" in login(other, "new@test.com", "customer", "password123").data  # AC3
    assert login(other, "new@test.com", "customer", temp).status_code == 302
    assert "/account/password" in other.get("/customer/").headers["Location"]                       # AC4
    assert "pbkdf2" not in page and "scrypt" not in page                                            # AC5


def test_ua17_review_reported_idps(ua, app):
    designer = make("designer", "des@test.com", "Dana")
    c1 = make("customer", "c1@test.com", "Cee One", phone="81110001")
    c2 = make("customer", "c2@test.com", "Cee Two", phone="81110002")
    old, new = (IDP(title=t, category="Kitchen", designer_id=designer.id) for t in ("Old Loft", "New Loft"))
    db.session.add_all([old, new])
    db.session.commit()
    Report.submit(c1.id, old.id, "Spam or advertising").created_at = datetime.now() - timedelta(days=3)
    Report.submit(c2.id, new.id, "Other")
    db.session.commit()
    page = text(ua.get("/admin/reports"))
    assert page.index("New Loft") < page.index("Old Loft")                                          # AC1
    for value in ("Spam or advertising", "Cee One", datetime.now().strftime("%Y")):                 # AC2
        assert value in page
    assert f"/customer/projects/{old.id}" in page                                                   # AC3
    assert "Mark resolved" in page and "Remove project" in page                                     # AC4
    first = Report.query.filter_by(idp_id=old.id).one()
    ua.post(f"/admin/reports/{first.id}/resolve")
    assert "Old Loft" not in text(ua.get("/admin/reports"))                                         # AC5
    assert "Old Loft" in text(ua.get("/admin/reports?status=resolved"))
    assert app.test_client().get(f"/customer/projects/{old.id}").status_code == 200                  # dismissed: stays
    second = Report.query.filter_by(idp_id=new.id).one()
    ua.post(f"/admin/reports/{second.id}/remove", data={"reason": "Spam"})
    assert app.test_client().get(f"/customer/projects/{new.id}").status_code == 404                  # removed: hidden


def test_ua18_announcements(ua, app):
    form = text(ua.get("/admin/announcements"))
    assert 'name="title"' in form and 'name="message"' in form and form.count("required") >= 2      # AC1
    assert b"both a title and a message" in ua.post("/admin/announcements", data={"title": "x", "message": ""}).data
    ua.post("/admin/announcements", data={"title": "Maintenance", "message": "Sunday 2am"})
    history = text(ua.get("/admin/announcements"))
    assert "Maintenance" in history and datetime.now().strftime("%Y") in history                    # AC3/AC4
    make("customer", "cus@test.com", "Sarah", phone="81112222")
    make("designer", "des@test.com", "Dana", phone="82223333")
    make("platform", "pm@test.com", "Pat", phone="83334444")
    for email, role, home in (("cus@test.com", "customer", "/"), ("des@test.com", "designer", "/designer/"),
                              ("pm@test.com", "platform", "/platform/"), ("admin@test.com", "admin", "/admin/")):
        c = app.test_client()
        login(c, email, role)
        assert "Maintenance" in text(c.get(home)), role                                             # AC2
