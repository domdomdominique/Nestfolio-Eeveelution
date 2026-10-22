"""ID-21 Interior designer views enquiries from customers (completes C-16 AC4)."""
from app.control.send_enquiry_controller import SendEnquiryController
from app.control.view_enquiries_controller import ViewEnquiriesController
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


def setup_data():
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    other = UserAccount.create("other@test.com", "password123", "designer", name="Olly Ng")
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    loft = IDP(title="Scandinavian Loft", category="Living Room", designer_id=designer.id)
    db.session.add(loft)
    db.session.commit()
    return designer, other, customer, loft


def login(client, email):
    client.post("/login", data={"email": email, "password": "password123"})


def test_customer_enquiry_appears_in_designers_list(app):
    designer, _, customer, loft = setup_data()
    SendEnquiryController().send(customer.id, designer.id, "Sarah", "sarah@mail.com",
                                 "Can you quote for my 4-room?", loft.id)
    enquiries = ViewEnquiriesController().view(designer.id)
    assert [(e.name, e.contact, e.idp.title) for e in enquiries] == \
        [("Sarah", "sarah@mail.com", "Scandinavian Loft")]


def test_designer_only_sees_their_own_enquiries(app):
    designer, other, customer, _ = setup_data()
    SendEnquiryController().send(customer.id, other.id, "Sarah", "9123 4567", "Hello Olly")
    assert ViewEnquiriesController().view(designer.id) == []
    assert ViewEnquiriesController().count(other.id) == 1


def test_enquiries_page_shows_messages_newest_first(client, app):
    designer, _, customer, loft = setup_data()
    controller = SendEnquiryController()
    controller.send(customer.id, designer.id, "Sarah", "sarah@mail.com", "First message")
    controller.send(customer.id, designer.id, "Sarah", "sarah@mail.com", "Second message", loft.id)
    login(client, "des@test.com")
    dashboard = client.get("/designer/").get_data(as_text=True)
    assert "Recent enquiries" in dashboard and "Second message" in dashboard
    assert '<span class="stat-value">2</span>' in dashboard
    page = client.get("/designer/enquiries").get_data(as_text=True)
    assert page.index("Second message") < page.index("First message")
    assert "Scandinavian Loft" in page and "sarah@mail.com" in page


def test_empty_enquiry_list_message(client, app):
    setup_data()
    login(client, "des@test.com")
    assert "No enquiries yet" in client.get("/designer/enquiries").get_data(as_text=True)


def test_only_designers_can_see_enquiries(client, app):
    setup_data()
    login(client, "cus@test.com")
    assert client.get("/designer/enquiries").status_code == 403
