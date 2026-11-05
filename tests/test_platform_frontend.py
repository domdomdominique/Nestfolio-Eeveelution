"""Platform Management pages (PM-03 to PM-11)."""
from datetime import date

from app.entity.db import db
from app.entity.idp import IDP
from app.entity.idp_category import IDPCategory
from app.entity.user_account import UserAccount


def login_platform(client):
    UserAccount.create("pm@test.com", "password123", "platform", name="Pat Lim")
    client.post("/login", data={"email": "pm@test.com", "password": "password123"})


def test_pages_need_platform_login(client, app):
    assert client.get("/platform/categories").status_code == 302
    assert client.get("/platform/reports").status_code == 302


def test_dashboard_and_category_list_load(client, app):
    login_platform(client)
    assert b"Welcome back" in client.get("/platform/").data
    assert b"Living Room" in client.get("/platform/categories").data


def test_create_edit_and_delete_category(client, app):
    login_platform(client)
    client.post("/platform/categories/new", data={"name": "Balcony", "description": "Outdoor"})
    category = IDPCategory.query.filter_by(name="Balcony").one()
    page = client.post(f"/platform/categories/{category.id}/edit",
                       data={"name": "Kitchen", "description": ""})
    assert b"already exists" in page.data
    client.post(f"/platform/categories/{category.id}/edit", data={"name": "Patio", "description": ""})
    assert IDPCategory.get(category.id).name == "Patio"
    client.post(f"/platform/categories/{category.id}/delete")
    assert IDPCategory.get(category.id) is None


def test_category_in_use_cannot_be_deleted(client, app):
    designer = UserAccount.create("d@test.com", "password123", "designer", name="D")
    db.session.add(IDP(title="Loft", category="Kitchen", designer_id=designer.id))
    db.session.commit()
    login_platform(client)
    kitchen = IDPCategory.query.filter_by(name="Kitchen").one()
    client.post(f"/platform/categories/{kitchen.id}/delete")
    assert IDPCategory.get(kitchen.id) is not None


def test_category_search_says_no_results(client, app):
    login_platform(client)
    assert b"No results found" in client.get("/platform/categories?q=zzzz").data


def test_report_page_and_downloads(client, app):
    login_platform(client)
    today = date.today().isoformat()
    page = client.get(f"/platform/reports?kind=daily&value={today}")
    assert b"Daily report" in page.data
    xlsx = client.get(f"/platform/reports/download?kind=daily&value={today}&format=xlsx")
    assert xlsx.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert f"daily_report_{today}.xlsx" in xlsx.headers["Content-Disposition"]
    pdf = client.get(f"/platform/reports/download?kind=daily&value={today}&format=pdf")
    assert pdf.data.startswith(b"%PDF")


def test_bad_report_date_shows_message(client, app):
    login_platform(client)
    assert b"valid date" in client.get("/platform/reports?kind=daily&value=nope").data


def test_far_future_dates_show_a_message_instead_of_crashing(client, app):
    login_platform(client)
    for kind, value in (("daily", "9999-12-31"), ("weekly", "9999-12-30"), ("monthly", "9999-12")):
        page = client.get(f"/platform/reports?kind={kind}&value={value}")
        assert page.status_code == 200 and b"valid date" in page.data
