"""ID-21 AC3 and AC5: designers reply to enquiries, customers see the reply and can answer,
with notification badges for new messages."""
import pytest

from app.control.enquiry_notification_controller import EnquiryNotificationController
from app.control.reply_to_enquiry_controller import ReplyToEnquiryController
from app.control.send_enquiry_controller import SendEnquiryController
from app.control.view_my_enquiries_controller import ViewMyEnquiriesController
from app.entity.enquiry import Enquiry
from app.entity.reply import Reply
from app.entity.user_account import UserAccount


def setup_people():
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    other = UserAccount.create("other@test.com", "password123", "customer", name="Olly")
    SendEnquiryController().send(customer.id, designer.id, "Sarah Tan", "cus@test.com",
                                 "Could you quote for my 4-room HDB?")  # returns the designer
    enquiry = Enquiry.query.one()
    return designer, customer, other, enquiry


def login(client, email, role):
    client.post("/login", data={"email": email, "password": "password123", "role": role})


# --- Control and Entity ---------------------------------------------------------------------

def test_designer_reply_is_saved_in_order(app):
    designer, customer, _, enquiry = setup_people()
    ReplyToEnquiryController().reply(designer.id, enquiry.id, "  Yes, from about S$40k.  ")
    ReplyToEnquiryController().reply(customer.id, enquiry.id, "Great, when can we meet?")
    assert [r.message for r in enquiry.replies] == ["Yes, from about S$40k.", "Great, when can we meet?"]
    assert enquiry.replies[0].from_designer and not enquiry.replies[1].from_designer


@pytest.mark.parametrize("message, error", [("", "Please write a reply"), ("   ", "Please write a reply"),
                                            ("x" * 2001, "under 2000 characters")])
def test_empty_or_too_long_reply_is_rejected(app, message, error):
    designer, _, _, enquiry = setup_people()
    with pytest.raises(ValueError, match=error):
        ReplyToEnquiryController().reply(designer.id, enquiry.id, message)
    assert Reply.query.count() == 0


def test_only_the_designer_and_customer_can_reply(app):
    designer, customer, other, enquiry = setup_people()
    other_designer = UserAccount.create("d2@test.com", "password123", "designer", name="Zed")
    for outsider in (other, other_designer):
        with pytest.raises(LookupError):
            ReplyToEnquiryController().reply(outsider.id, enquiry.id, "hi")
    with pytest.raises(LookupError):
        ReplyToEnquiryController().reply(designer.id, 999, "hi")
    assert Reply.query.count() == 0


def test_suspended_designer_cannot_reply(app):
    designer, _, _, enquiry = setup_people()
    designer.set_suspended(True)
    with pytest.raises(LookupError):
        ReplyToEnquiryController().reply(designer.id, enquiry.id, "hi")


def test_customer_sees_only_their_own_enquiries(app):
    designer, customer, other, enquiry = setup_people()
    assert ViewMyEnquiriesController().view(customer.id) == [enquiry]
    assert ViewMyEnquiriesController().view(other.id) == []
    with pytest.raises(LookupError):
        ViewMyEnquiriesController().view(designer.id)


# --- Notifications ----------------------------------------------------------------------------

def test_new_enquiry_notifies_the_designer_until_seen(app):
    designer, customer, _, enquiry = setup_people()
    notes = EnquiryNotificationController()
    assert notes.unread_count(designer.id) == 1 and notes.unread_count(customer.id) == 0
    notes.mark_seen(designer.id, [enquiry])
    assert notes.unread_count(designer.id) == 0


def test_reply_notifies_the_other_person(app):
    designer, customer, _, enquiry = setup_people()
    notes = EnquiryNotificationController()
    notes.mark_seen(designer.id, [enquiry])
    ReplyToEnquiryController().reply(designer.id, enquiry.id, "Yes!")
    assert notes.unread_count(customer.id) == 1 and notes.unread_count(designer.id) == 0  # own reply isn't new
    notes.mark_seen(customer.id, [enquiry])
    ReplyToEnquiryController().reply(customer.id, enquiry.id, "Thanks")
    assert notes.unread_count(customer.id) == 0 and notes.unread_count(designer.id) == 1


# --- Pages ------------------------------------------------------------------------------------

def test_designer_replies_from_the_enquiries_page(client, app):
    designer, customer, _, enquiry = setup_people()
    login(client, "des@test.com", "designer")
    page = client.get("/designer/").get_data(as_text=True)
    assert 'aria-label="1 new"' in page                                     # badge on the sidebar
    page = client.get("/designer/enquiries").get_data(as_text=True)
    assert "Could you quote" in page and "Awaiting reply" in page and ">New<" in page and "Reply" in page
    response = client.post(f"/designer/enquiries/{enquiry.id}/reply", data={"message": "Yes, let's talk."},
                           follow_redirects=True)
    page = response.get_data(as_text=True)
    assert "Reply sent to Sarah Tan." in page and "Yes, let&#39;s talk." in page and "Replied" in page
    assert 'aria-label="1 new"' not in page                                 # seen, so the badge is gone


def test_customer_sees_reply_and_badge_then_answers(client, app):
    designer, customer, _, enquiry = setup_people()
    ReplyToEnquiryController().reply(designer.id, enquiry.id, "Yes, from about S$40k.")
    login(client, "cus@test.com", "customer")
    home = client.get("/customer/").get_data(as_text=True)
    assert "My Enquiries" in home and 'aria-label="1 new"' in home         # navbar badge
    page = client.get("/customer/enquiries").get_data(as_text=True)
    assert "Yes, from about S$40k." in page and "New reply" in page and "Dana Ong" in page
    page = client.post(f"/customer/enquiries/{enquiry.id}/reply", data={"message": "When can we meet?"},
                       follow_redirects=True).get_data(as_text=True)
    assert "Message sent to" in page and "When can we meet?" in page and "New reply" not in page


def test_empty_reply_from_page_shows_error(client, app):
    designer, _, _, enquiry = setup_people()
    login(client, "des@test.com", "designer")
    page = client.post(f"/designer/enquiries/{enquiry.id}/reply", data={"message": " "},
                       follow_redirects=True).get_data(as_text=True)
    assert "Please write a reply or attach a file before sending." in page and Reply.query.count() == 0


def test_other_users_get_404_and_pages_need_login(client, app):
    designer, customer, other, enquiry = setup_people()
    assert client.get("/customer/enquiries").status_code == 302              # must log in
    login(client, "other@test.com", "customer")
    assert client.post(f"/customer/enquiries/{enquiry.id}/reply", data={"message": "hi"}).status_code == 404
    assert client.get("/designer/enquiries").status_code in (302, 403)


# --- Two-pane inbox: tabs, search, opening one conversation -----------------------------------

def test_inbox_opens_newest_conversation_and_marks_only_that_one_seen(app):
    from app.control.enquiry_inbox_controller import EnquiryInboxController

    designer, customer, _, first = setup_people()
    SendEnquiryController().send(customer.id, designer.id, "Sarah Tan", "cus@test.com", "Second question")
    second = Enquiry.query.filter_by(message="Second question").one()
    inbox = EnquiryInboxController().open(designer.id, Enquiry.for_designer(designer.id))
    assert inbox["enquiries"][0].id == inbox["selected"].id == second.id
    assert inbox["counts"] == {"all": 2, "unread": 2, "replied": 0}
    assert EnquiryNotificationController().unread_count(designer.id) == 1   # the other one is still new

    inbox = EnquiryInboxController().open(designer.id, Enquiry.for_designer(designer.id), selected_id=first.id)
    assert inbox["selected"].id == first.id
    assert EnquiryNotificationController().unread_count(designer.id) == 0


def test_inbox_tabs_and_search(app):
    from app.control.enquiry_inbox_controller import EnquiryInboxController

    designer, customer, _, first = setup_people()
    SendEnquiryController().send(customer.id, designer.id, "Sarah Tan", "cus@test.com", "Kitchen budget?")
    ReplyToEnquiryController().reply(designer.id, first.id, "Sure, about S$40k.")
    controller = EnquiryInboxController()
    replied = controller.open(designer.id, Enquiry.for_designer(designer.id), show="replied")
    assert [e.id for e in replied["enquiries"]] == [first.id]
    found = controller.open(designer.id, Enquiry.for_designer(designer.id), search="KITCHEN")
    assert [e.message for e in found["enquiries"]] == ["Kitchen budget?"]
    found = controller.open(designer.id, Enquiry.for_designer(designer.id), search="S$40k")   # searches replies too
    assert [e.id for e in found["enquiries"]] == [first.id]
    assert controller.open(designer.id, [], search="x")["selected"] is None


def test_inbox_page_shows_conversation_with_header_and_reply_box(client, app):
    designer, _, _, enquiry = setup_people()
    login(client, "des@test.com", "designer")
    page = client.get(f"/designer/enquiries?id={enquiry.id}").get_data(as_text=True)
    assert "All (1)" in page and "Unread (1)" in page and "Replied (0)" in page
    assert "Today" in page and "cus@test.com" in page and "Send reply" in page and "General company enquiry" in page
    page = client.get("/designer/enquiries?q=nothing-matches").get_data(as_text=True)
    assert "No results found" in page


def test_short_times():
    from datetime import datetime, timedelta

    from app.boundary.timefmt import ago, clock, day_label, initials

    now = datetime(2026, 11, 5, 12, 0)
    assert [ago(now - d, now) for d in (timedelta(seconds=5), timedelta(minutes=7), timedelta(hours=2),
                                         timedelta(days=3), timedelta(days=8))] == ["now", "7m", "2h", "3d", "1w"]
    assert clock(datetime(2026, 1, 1, 10, 12)) == "10:12 am" and clock(datetime(2026, 1, 1, 13, 5)) == "1:05 pm"
    assert day_label(now, now.date()) == "Today" and day_label(now - timedelta(days=1), now.date()) == "Yesterday"
    assert initials("Sarah Tan") == "ST" and initials("Oakline & Co Studio") == "OC"


# --- C-16 'Send enquiry' button opens the messaging page ------------------------------------

def _project(designer, title="Warm Scandinavian 4-room HDB"):
    from app.entity.db import db
    from app.entity.idp import IDP

    idp = IDP(title=title, category="Living Room", designer_id=designer.id)
    db.session.add(idp)
    db.session.commit()
    return idp


def test_project_page_button_opens_new_conversation_then_sends(client, app):
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    idp = _project(designer)
    login(client, "cus@test.com", "customer")
    page = client.get(f"/customer/projects/{idp.id}").get_data(as_text=True)
    link = f"/customer/enquiries/new?designer_id={designer.id}&amp;idp_id={idp.id}"
    assert link in page and "Send enquiry" in page                                # button on the project page

    compose = client.get(link.replace("&amp;", "&")).get_data(as_text=True)
    assert "New enquiry" in compose and "About:" in compose and idp.title in compose
    assert 'value="Sarah Tan"' in compose and 'value="cus@test.com"' in compose     # filled in from the account

    sent = client.post(f"/customer/designers/{designer.id}/enquiry",
                       data={"name": "Sarah Tan", "contact": "cus@test.com", "message": "Love this look!",
                             "idp_id": idp.id})
    enquiry = Enquiry.query.one()
    assert sent.headers["Location"].endswith(f"/customer/enquiries?id={enquiry.id}")  # straight to the chat
    page = client.get(sent.headers["Location"]).get_data(as_text=True)
    assert "Love this look!" in page and "Waiting for a reply" in page

    again = client.get(link.replace("&amp;", "&"))                                 # no duplicate conversation
    assert again.headers["Location"].endswith(f"/customer/enquiries?id={enquiry.id}")


def test_new_enquiry_errors_keep_the_message(client, app):
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    login(client, "cus@test.com", "customer")
    page = client.post(f"/customer/designers/{designer.id}/enquiry",
                       data={"name": "Sarah", "contact": "123", "message": "Keep me"}).get_data(as_text=True)
    assert "valid email address" in page and "Keep me</textarea>" in page and Enquiry.query.count() == 0


def test_send_enquiry_button_for_visitors_and_designers(client, app):
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    idp = _project(designer)
    page = client.get(f"/customer/projects/{idp.id}").get_data(as_text=True)
    assert "/login?next=" in page and "Send enquiry" in page                         # visitors log in first
    assert client.get(f"/customer/enquiries/new?designer_id={designer.id}").status_code == 302
    login(client, "des@test.com", "designer")
    assert "/customer/enquiries/new" not in client.get(f"/customer/projects/{idp.id}").get_data(as_text=True)
    UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    client.get("/logout")
    login(client, "cus@test.com", "customer")
    assert client.get("/customer/enquiries/new?designer_id=999").status_code == 404
