"""UA-17 User Admin reviews reported IDPs (completes C-15 AC4)."""
import pytest

from app.control.report_idp_controller import ReportIDPController
from app.control.review_reports_controller import ReviewReportsController
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.report import Report
from app.entity.user_account import UserAccount


def setup_data():
    admin = UserAccount.create("admin@test.com", "password123", "admin")
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    loft = IDP(title="Scandinavian Loft", category="Living Room", designer_id=designer.id)
    db.session.add(loft)
    db.session.commit()
    return admin, customer, loft


def login(client, email):
    client.post("/login", data={"email": email, "password": "password123"})


def test_customer_report_appears_in_admin_open_list(app):
    _, customer, loft = setup_data()
    ReportIDPController().report(customer.id, loft.id, "Spam or advertising", "Selling packages")
    reports = ReviewReportsController().list_reports("open")
    assert [(r.idp.title, r.reason, r.customer.name) for r in reports] == \
        [("Scandinavian Loft", "Spam or advertising", "Sarah Tan")]
    assert ReviewReportsController().open_count() == 1


def test_resolving_moves_report_to_resolved(app):
    admin, customer, loft = setup_data()
    report = ReportIDPController().report(customer.id, loft.id, "Other")
    controller = ReviewReportsController()
    controller.resolve(report.id, admin.id)
    assert controller.list_reports("open") == []
    assert [r.id for r in controller.list_reports("resolved")] == [report.id]
    assert (report.resolved_by, report.resolved_at is not None) == (admin.id, True)


def test_report_cannot_be_resolved_twice_or_if_missing(app):
    admin, customer, loft = setup_data()
    report = ReportIDPController().report(customer.id, loft.id, "Other")
    controller = ReviewReportsController()
    controller.resolve(report.id, admin.id)
    with pytest.raises(ValueError, match="already been resolved"):
        controller.resolve(report.id, admin.id)
    with pytest.raises(ValueError, match="not found"):
        controller.resolve(999, admin.id)


def test_unknown_status_shows_open_reports(app):
    _, customer, loft = setup_data()
    ReportIDPController().report(customer.id, loft.id, "Other")
    assert len(ReviewReportsController().list_reports("nonsense")) == 1


def test_admin_reports_page_lists_and_resolves(client, app):
    _, customer, loft = setup_data()
    report = ReportIDPController().report(customer.id, loft.id, "Spam or advertising")
    login(client, "admin@test.com")
    assert "1 report waiting" in client.get("/admin/").get_data(as_text=True)
    page = client.get("/admin/reports").get_data(as_text=True)
    assert "Scandinavian Loft" in page and "Spam or advertising" in page
    response = client.post(f"/admin/reports/{report.id}/resolve", follow_redirects=True)
    assert "Report marked as resolved" in response.get_data(as_text=True)
    assert Report.count_open() == 0


def test_only_admins_can_see_reports(client, app):
    setup_data()
    login(client, "cus@test.com")
    assert client.get("/admin/reports").status_code == 403
