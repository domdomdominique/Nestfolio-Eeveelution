"""UA-17 page works in the browser (dialog is in the page), UA-18 reaches customers, C-16 contact is checked."""
import pytest

from app.control.report_idp_controller import ReportIDPController
from app.control.send_announcement_controller import SendAnnouncementController
from app.control.send_enquiry_controller import SendEnquiryController
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


def setup_data():
    admin = UserAccount.create("admin@test.com", "password123", "admin")
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana")
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Sam")
    idp = IDP(title="Scandinavian Loft", category="Living Room", designer_id=designer.id)
    db.session.add(idp)
    db.session.commit()
    return admin, designer, customer, idp


def login(client, email):
    client.post("/login", data={"email": email, "password": "password123"})


def test_remove_dialog_is_in_the_page_body_and_removing_works(client, app):
    admin, _, customer, idp = setup_data()
    report = ReportIDPController().report(customer.id, idp.id, "Spam or advertising")
    login(client, "admin@test.com")
    html = client.get("/admin/reports").get_data(as_text=True)
    head = html[:html.index("</head>")]
    assert "<dialog" not in head and 'id="remove-dialog"' in html
    assert f"/admin/reports/{report.id}/remove" in html
    # both actions only open a confirmation dialog; neither is a direct submit button
    assert 'id="resolve-dialog"' in html and 'data-open="resolve-dialog"' in html
    assert f' action="/admin/reports/{report.id}/resolve"' not in html
    client.post(f"/admin/reports/{report.id}/remove")
    assert idp.is_removed


def test_logged_in_customer_sees_announcements_on_browse(client, app):
    admin, _, _, _ = setup_data()
    SendAnnouncementController().send(admin.id, "Maintenance", "Sunday 2am")
    assert b"Maintenance" not in client.get("/customer/").data  # public visitors do not see it
    login(client, "cus@test.com")
    assert b"Maintenance" in client.get("/customer/").data


def test_designer_sees_announcements_on_dashboard(client, app):
    admin, _, _, _ = setup_data()
    SendAnnouncementController().send(admin.id, "Maintenance", "Sunday 2am")
    login(client, "des@test.com")
    assert b"Maintenance" in client.get("/designer/").data


@pytest.mark.parametrize("contact, stored", [
    ("Sam@Test.com", "sam@test.com"), ("9123 4567", "+65 91234567"), ("+65 91234567", "+65 91234567"),
])
def test_enquiry_contact_accepts_email_or_sg_phone(app, contact, stored):
    _, designer, customer, _ = setup_data()
    SendEnquiryController().send(customer.id, designer.id, "Sam", contact, "Hello")
    from app.entity.enquiry import Enquiry
    assert Enquiry.query.one().contact == stored


@pytest.mark.parametrize("contact", ["abc", "12345", "a@b", "5123 4567"])
def test_enquiry_contact_rejects_junk(app, contact):
    _, designer, customer, _ = setup_data()
    with pytest.raises(ValueError, match="valid email address or 8-digit"):
        SendEnquiryController().send(customer.id, designer.id, "Sam", contact, "Hello")


def test_admin_can_remove_an_announcement(client, app):
    admin, _, _, _ = setup_data()
    keep = SendAnnouncementController().send(admin.id, "Keep me", "Stays")
    gone = SendAnnouncementController().send(admin.id, "Maintenance", "Sunday 2am")
    login(client, "admin@test.com")
    page = client.get("/admin/announcements").get_data(as_text=True)
    assert f"/admin/announcements/{gone.id}/remove" in page and 'id="remove-dialog"' in page
    client.post(f"/admin/announcements/{gone.id}/remove")
    assert [a.title for a in SendAnnouncementController().history()] == ["Keep me"]
    assert client.post("/admin/announcements/9999/remove").status_code == 302  # unknown id: no crash
    login(client, "cus@test.com")
    assert b"Maintenance" not in client.get("/customer/").data


def test_only_admin_can_remove_announcements(client, app):
    admin, _, _, _ = setup_data()
    a = SendAnnouncementController().send(admin.id, "Maintenance", "Sunday 2am")
    login(client, "cus@test.com")
    assert client.post(f"/admin/announcements/{a.id}/remove").status_code in (302, 403)
    assert len(SendAnnouncementController().history()) == 1


@pytest.mark.parametrize("role, nav", [("admin", "/admin/"), ("platform", "/platform/")])
def test_admin_and_platform_can_change_their_own_password(client, app, role, nav):
    UserAccount.create(f"{role}@test.com", "password123", role)
    login(client, f"{role}@test.com")
    assert b"/account/password" in client.get(nav).data  # sidebar link
    page = client.get("/account/password").get_data(as_text=True)
    assert "Current password" in page and "temporary" not in page.lower()
    client.post("/account/password", data={"current_password": "password123",
                                           "new_password": "brandnew123", "confirm_password": "brandnew123"})
    from app.control.login_controller import LoginController
    assert LoginController().login(f"{role}@test.com", "password123") is None
    assert LoginController().login(f"{role}@test.com", "brandnew123") is not None
