"""User Admin dashboard: activity charts of accounts, applications and reports per day."""
from datetime import datetime, timedelta

from app.control.view_admin_activity_controller import ViewAdminActivityController
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.report import Report
from app.entity.user_account import UserAccount


def setup_records():
    """Today: 4 accounts (admin, designer, 2 customers), 1 report filed and resolved.
    Two days ago: 1 more report, still open."""
    admin = UserAccount.create("admin@test.com", "password123", "admin", name="Ann Admin")
    designer = UserAccount.create("d@test.com", "password123", "designer", name="Des")
    customer = UserAccount.create("c@test.com", "password123", "customer", name="Cus")
    other = UserAccount.create("e@test.com", "password123", "customer", name="Eve")
    idp = IDP(title="Loft", category="Kitchen", designer_id=designer.id)
    db.session.add(idp)
    db.session.commit()
    now = datetime.now()
    db.session.add(Report(idp_id=idp.id, customer_id=customer.id, reason="Other", created_at=now,
                          status="resolved", resolved_at=now, resolution="dismissed", resolved_by=admin.id))
    db.session.add(Report(idp_id=idp.id, customer_id=other.id, reason="Other",
                          created_at=now - timedelta(days=2)))
    db.session.commit()


def test_activity_counts_per_day(app):
    setup_records()
    activity = ViewAdminActivityController().activity(7)
    series = {s["unit"]: s for s in activity["series"]}
    assert activity["days"] == 7 and len(activity["labels"]) == 7
    assert series["accounts"]["counts"][-1] == 4 and series["accounts"]["total"] == 4
    assert series["reports"]["counts"][-3:] == [1, 0, 1] and series["reports"]["total"] == 2
    assert series["resolved"]["total"] == 1
    assert series["applications"]["total"] == 0


def test_unknown_period_falls_back_to_30_days(app):
    assert ViewAdminActivityController().activity(12)["days"] == 30
    assert ViewAdminActivityController().activity(None)["days"] == 30


def test_admin_home_shows_activity_charts(client, app):
    setup_records()
    client.post("/login", data={"email": "admin@test.com", "password": "password123"})
    page = client.get("/admin/?days=7").get_data(as_text=True)
    assert "Projects reported" in page and "New user accounts" in page
    assert "Per day over the last 7 days" in page
    assert page.count("<svg viewBox") >= 4


def test_activity_compares_with_the_days_before(app):
    setup_records()
    old = UserAccount.query.filter_by(email="e@test.com").one()
    old.created_at = datetime.now() - timedelta(days=10)   # in the 7 days before the last 7
    db.session.commit()
    series = {s["unit"]: s for s in ViewAdminActivityController().activity(7)["series"]}
    assert (series["accounts"]["total"], series["accounts"]["previous"]) == (3, 1)
    assert series["accounts"]["change"] == 200 and series["accounts"]["change_text"] == "+200%"
    assert series["reports"]["change"] == "new"
    assert series["applications"]["change"] is None and series["applications"]["change_text"] == "-"

