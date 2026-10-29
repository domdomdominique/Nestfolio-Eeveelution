"""UA-18: User Admin sends system-wide announcements."""
import pytest

from app.control.send_announcement_controller import SendAnnouncementController
from app.entity.user_account import UserAccount


def make_admin():
    return UserAccount.create("admin@test.com", "password123", "admin", name="Admin")


def test_sent_announcement_has_a_date_and_shows_newest_first(app):
    admin = make_admin()
    controller = SendAnnouncementController()
    first = controller.send(admin.id, "Maintenance", "Down on Sunday 2am.")
    second = controller.send(admin.id, " New categories ", " Balcony added. ")
    assert second.title == "New categories" and second.message == "Balcony added."
    assert first.sent_at is not None
    assert controller.history() == [second, first]
    assert controller.latest(limit=1) == [second]


@pytest.mark.parametrize("title, message", [("", "Hello"), ("Hello", "   "), ("x" * 151, "Hello")])
def test_title_and_message_are_required(app, title, message):
    admin = make_admin()
    with pytest.raises(ValueError):
        SendAnnouncementController().send(admin.id, title, message)
    assert SendAnnouncementController().history() == []
