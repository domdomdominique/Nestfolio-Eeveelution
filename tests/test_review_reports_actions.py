"""UA-17: User Admin dismisses a report or removes the reported IDP."""
import pytest

from app.control.report_idp_controller import ReportIDPController
from app.control.review_reports_controller import ReviewReportsController
from app.control.search_idp_controller import SearchIDPController
from app.control.view_idp_controller import ViewIDPController
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.report import Report
from app.entity.user_account import UserAccount


def setup_data():
    admin = UserAccount.create("admin@test.com", "password123", "admin")
    designer = UserAccount.create("des@test.com", "password123", "designer")
    c1 = UserAccount.create("c1@test.com", "password123", "customer")
    c2 = UserAccount.create("c2@test.com", "password123", "customer")
    idp = IDP(title="Scandinavian Loft", category="Living Room", designer_id=designer.id)
    db.session.add(idp)
    db.session.commit()
    r1 = ReportIDPController().report(c1.id, idp.id, "Spam or advertising")
    r2 = ReportIDPController().report(c2.id, idp.id, "Other")
    return admin, idp, r1, r2


def test_dismiss_keeps_the_idp_visible(app):
    admin, idp, r1, _ = setup_data()
    ReviewReportsController().dismiss(r1.id, admin.id)
    assert (r1.status, r1.resolution) == ("resolved", "dismissed")
    assert idp in SearchIDPController().browse()


def test_remove_hides_the_idp_and_closes_all_its_reports(app):
    admin, idp, r1, r2 = setup_data()
    ReviewReportsController().remove_idp(r1.id, admin.id, "Spam")
    assert idp.is_removed and not idp.is_visible
    assert idp not in SearchIDPController().browse()
    with pytest.raises(LookupError):
        ViewIDPController().view(idp.id)
    assert {r.resolution for r in (r1, r2)} == {"removed"}
    assert Report.count_open() == 0


def test_resolved_reports_leave_the_open_list(app):
    admin, _, r1, r2 = setup_data()
    ReviewReportsController().dismiss(r1.id, admin.id)
    assert ReviewReportsController().list_reports("open") == [r2]
    assert ReviewReportsController().list_reports("resolved") == [r1]


def test_cannot_remove_from_an_already_resolved_report(app):
    admin, idp, r1, _ = setup_data()
    ReviewReportsController().dismiss(r1.id, admin.id)
    with pytest.raises(ValueError, match="already been resolved"):
        ReviewReportsController().remove_idp(r1.id, admin.id, "Spam")
    assert not idp.is_removed


def test_remove_needs_a_reason_and_keeps_it(app):
    admin, idp, r1, r2 = setup_data()
    with pytest.raises(ValueError, match="reason"):
        ReviewReportsController().remove_idp(r1.id, admin.id, "  ")
    assert not idp.is_removed
    ReviewReportsController().remove_idp(r1.id, admin.id, "Copied content")
    assert r1.removal_reason == r2.removal_reason == "Copied content"


def test_reason_with_crlf_line_breaks_counts_as_one_character(app):
    admin, _, r1, _ = setup_data()
    ReviewReportsController().remove_idp(r1.id, admin.id, "a\r\n" * 200 + "b" * 100)  # 500 in a browser, 700 raw
    assert r1.status == "resolved"
