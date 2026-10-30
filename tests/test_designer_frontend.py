"""Designer pages: announcements on the dashboard (UA-18) and sidebar highlight."""
from app.control.send_announcement_controller import SendAnnouncementController
from app.entity.user_account import UserAccount


def login_designer(client):
    UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    client.post("/login", data={"email": "des@test.com", "password": "password123"})


def test_dashboard_shows_latest_announcement(client, app):
    admin = UserAccount.create("admin@test.com", "password123", "admin", name="Ann")
    SendAnnouncementController().send(admin.id, "Maintenance", "Down on Sunday 2am.")
    login_designer(client)
    page = client.get("/designer/").get_data(as_text=True)
    assert "Maintenance" in page and "Down on Sunday 2am." in page


def test_dashboard_has_no_announcement_box_when_none_sent(client, app):
    login_designer(client)
    assert "Announcements" not in client.get("/designer/").get_data(as_text=True)


def test_enquiries_page_highlights_its_sidebar_link(client, app):
    login_designer(client)
    page = client.get("/designer/enquiries").get_data(as_text=True)
    assert 'href="/designer/enquiries" aria-current="page"' in page
