"""Changes from review feedback:
- UA-18 announcements can be pushed to selected roles only, and the box is centred.
- C-16 enquiries can carry photos (JPG/PNG) and PDFs that only the two people in the conversation can open.
- PM-04 a category's page lists its IDPs, not only how many there are.
"""
from io import BytesIO

import pytest
from PIL import Image

from app.control.send_announcement_controller import SendAnnouncementController
from app.control.send_enquiry_controller import SendEnquiryController
from app.control.view_category_controller import ViewCategoryController
from app.entity.db import db
from app.entity.enquiry import Enquiry
from app.entity.enquiry_attachment import EnquiryAttachment
from app.entity.idp import IDP
from app.entity.idp_category import IDPCategory
from app.entity.user_account import UserAccount


def login(client, email):
    client.post("/login", data={"email": email, "password": "password123"})


def png_bytes():
    out = BytesIO()
    Image.new("RGB", (8, 8), "white").save(out, "PNG")
    return out.getvalue()


PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


class Upload:
    """A stand-in for an uploaded file in controller tests."""

    def __init__(self, filename, data):
        self.filename, self.stream = filename, BytesIO(data)


# --- UA-18 Announcements to selected roles -----------------------------------------------

def test_announcement_to_selected_roles_only_reaches_those_roles(app):
    admin = UserAccount.create("admin@test.com", "password123", "admin")
    controller = SendAnnouncementController()
    controller.send(admin.id, "Everyone", "For all")
    controller.send(admin.id, "Designers", "Portfolio tips", roles=["designer"])
    controller.send(admin.id, "Shoppers", "Sale week", roles=["customer", "platform"])

    def titles(role):
        return [a.title for a in controller.latest(10, role=role)]

    assert titles("designer") == ["Designers", "Everyone"]
    assert titles("customer") == ["Shoppers", "Everyone"]
    assert titles("platform") == ["Shoppers", "Everyone"]
    assert titles("admin") == ["Everyone"]
    assert len(controller.history()) == 3  # the admin's history shows every one


def test_announcement_role_choice_is_checked(app):
    admin = UserAccount.create("admin@test.com", "password123", "admin")
    controller = SendAnnouncementController()
    with pytest.raises(ValueError, match="at least one role"):
        controller.send(admin.id, "T", "M", roles=[])
    with pytest.raises(ValueError, match="roles from the list"):
        controller.send(admin.id, "T", "M", roles=["nobody"])
    every_role = [key for key, _ in controller.role_choices()]
    assert controller.send(admin.id, "T", "M", roles=every_role).is_for_everyone


def test_admin_page_sends_to_selected_roles_and_labels_history(client, app):
    UserAccount.create("admin@test.com", "password123", "admin")
    UserAccount.create("des@test.com", "password123", "designer", name="Dana")
    UserAccount.create("cus@test.com", "password123", "customer", name="Sam")
    login(client, "admin@test.com")
    page = client.get("/admin/announcements").get_data(as_text=True)
    assert 'name="audience"' in page and 'value="designer"' in page

    sent = client.post("/admin/announcements", follow_redirects=True, data={
        "title": "Designer briefing", "message": "New photo rules", "audience": "roles", "roles": ["designer"]})
    html = sent.get_data(as_text=True)
    assert "Announcement sent to Interior Designer." in html and "To: Interior Designer" in html

    client.post("/admin/announcements", data={"title": "Hello everyone", "message": "Hi", "audience": "all"})
    none_ticked = client.post("/admin/announcements", data={"title": "x", "message": "y", "audience": "roles"})
    assert b"at least one role" in none_ticked.data

    client.get("/logout")
    login(client, "des@test.com")
    dashboard = client.get("/designer/").data
    assert b"Designer briefing" in dashboard and b"Hello everyone" in dashboard
    client.get("/logout")
    login(client, "cus@test.com")
    home = client.get("/").data
    assert b"Designer briefing" not in home and b"Hello everyone" in home


def test_announcement_box_is_centred_with_left_padded_text(client, app):
    css = client.get("/static/css/site.css").get_data(as_text=True)
    block = css.split(".announcements {", 1)[1].split("}", 1)[0]
    assert "margin: 0 auto" in block and "max-width" in block  # box centred in its section
    assert "text-align: left" in block and "padding: 20px 24px 20px 32px" in block  # text padded left


# --- C-16 Enquiry attachments ------------------------------------------------------------

def people():
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana")
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Sam")
    return designer, customer


def test_enquiry_saves_photo_and_pdf_attachments(app):
    designer, customer = people()
    SendEnquiryController().send(customer.id, designer.id, "Sam", "cus@test.com", "See my floor plan",
                                 files=[Upload("room.png", png_bytes()), Upload("plan.pdf", PDF)])
    enquiry = Enquiry.query.one()
    assert [(a.filename, a.content_type) for a in enquiry.attachments] == [
        ("room.png", "image/png"), ("plan.pdf", "application/pdf")]
    assert enquiry.conversation[0].attachments == enquiry.attachments


@pytest.mark.parametrize("files, error", [
    ([Upload("notes.txt", b"hello")], "Only JPG, PNG and PDF"),
    ([Upload("fake.pdf", b"not a pdf")], "not a valid PDF"),
    ([Upload("fake.png", b"not an image")], "not a valid JPG or PNG"),
    ([Upload("big.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024))], "5 MB or smaller"),
    ([Upload(f"p{n}.pdf", PDF) for n in range(6)], "at most 5 files"),
])
def test_bad_attachments_are_rejected_and_nothing_is_saved(app, files, error):
    designer, customer = people()
    with pytest.raises(ValueError, match=error):
        SendEnquiryController().send(customer.id, designer.id, "Sam", "cus@test.com", "Hi", files=files)
    assert Enquiry.query.count() == 0 and EnquiryAttachment.query.count() == 0


def test_customer_uploads_through_the_form_and_both_sides_can_open_it(client, app):
    designer, customer = people()
    UserAccount.create("other@test.com", "password123", "customer", name="Olly")
    login(client, "cus@test.com")
    compose = client.get(f"/customer/enquiries/new?designer_id={designer.id}").get_data(as_text=True)
    assert 'enctype="multipart/form-data"' in compose and 'name="attachments"' in compose

    client.post(f"/customer/designers/{designer.id}/enquiry", content_type="multipart/form-data", data={
        "name": "Sam", "contact": "cus@test.com", "message": "Photos attached",
        "attachments": [(BytesIO(png_bytes()), "room.png"), (BytesIO(PDF), "plan.pdf")]})
    photo, pdf = Enquiry.query.one().attachments

    page = client.get(f"/customer/enquiries?id={photo.enquiry_id}").get_data(as_text=True)
    assert f"/customer/enquiries/attachments/{photo.id}" in page and "plan.pdf" in page
    shown = client.get(f"/customer/enquiries/attachments/{photo.id}")
    assert shown.status_code == 200 and shown.mimetype == "image/png"
    assert "sandbox" in shown.headers["Content-Security-Policy"]
    download = client.get(f"/customer/enquiries/attachments/{pdf.id}")
    assert download.data == PDF and "attachment" in download.headers["Content-Disposition"]

    client.get("/logout")
    login(client, "des@test.com")
    page = client.get(f"/designer/enquiries?id={photo.enquiry_id}").get_data(as_text=True)
    assert f"/designer/enquiries/attachments/{pdf.id}" in page
    assert client.get(f"/designer/enquiries/attachments/{pdf.id}").data == PDF

    client.get("/logout")
    login(client, "other@test.com")
    assert client.get(f"/customer/enquiries/attachments/{photo.id}").status_code == 404


# --- PM-04 Category shows its IDPs -------------------------------------------------------

def test_category_page_lists_its_projects(client, app):
    UserAccount.create("pm@test.com", "password123", "platform")
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana")
    db.session.add_all([
        IDP(title="Cosy Kitchen", category="Kitchen", designer_id=designer.id, is_current=True),
        IDP(title="Hidden Kitchen", category="Kitchen", designer_id=designer.id, is_removed=True),
        IDP(title="Calm Bedroom", category="Bedroom", designer_id=designer.id),
    ])
    db.session.commit()
    kitchen = IDPCategory.query.filter_by(name="Kitchen").one()
    assert [p.title for p in ViewCategoryController().projects(kitchen, "cosy")] == ["Cosy Kitchen"]

    login(client, "pm@test.com")
    html = client.get(f"/platform/categories/{kitchen.id}").get_data(as_text=True)
    assert "Cosy Kitchen" in html and "Hidden Kitchen" in html and "Calm Bedroom" not in html
    assert "Removed by an admin" in html and "Dana" in html
    searched = client.get(f"/platform/categories/{kitchen.id}?q=hidden").get_data(as_text=True)
    assert "Hidden Kitchen" in searched and "Cosy Kitchen" not in searched


def test_category_page_with_many_projects_pages_without_crashing(client, app):
    """Regression: the page links lost the category id, so a category with over 20 IDPs crashed."""
    UserAccount.create("pm@test.com", "password123", "platform")
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana")
    db.session.add_all([IDP(title=f"Kitchen {n:02}", category="Kitchen", designer_id=designer.id)
                        for n in range(25)])
    db.session.commit()
    kitchen = IDPCategory.query.filter_by(name="Kitchen").one()
    login(client, "pm@test.com")
    first = client.get(f"/platform/categories/{kitchen.id}")
    assert first.status_code == 200 and f"/platform/categories/{kitchen.id}?page=2" in first.get_data(as_text=True)
    second = client.get(f"/platform/categories/{kitchen.id}?page=2&q=kitchen")
    assert second.status_code == 200 and second.get_data(as_text=True).count("<tr>") == 1 + 5  # header + 5 left


# --- ID-21 / C-16 Attachments on replies, both ways ----------------------------------------

def test_designer_and_customer_can_attach_files_to_replies(client, app):
    designer, customer = people()
    SendEnquiryController().send(customer.id, designer.id, "Sam", "cus@test.com", "Hi")
    enquiry = Enquiry.query.one()

    login(client, "des@test.com")
    form = client.get(f"/designer/enquiries?id={enquiry.id}").get_data(as_text=True)
    assert form.count('enctype="multipart/form-data"') == 1 and 'name="attachments"' in form
    client.post(f"/designer/enquiries/{enquiry.id}/reply", content_type="multipart/form-data", data={
        "message": "Here is our quote", "attachments": [(BytesIO(PDF), "quote.pdf")]})
    quote = enquiry.replies[0].attachments[0]
    assert quote.filename == "quote.pdf" and quote.enquiry_id == enquiry.id
    client.get("/logout")

    # The customer sees the designer's file, and answers with only a photo (no text)
    login(client, "cus@test.com")
    page = client.get(f"/customer/enquiries?id={enquiry.id}").get_data(as_text=True)
    assert f"/customer/enquiries/attachments/{quote.id}" in page
    assert client.get(f"/customer/enquiries/attachments/{quote.id}").data == PDF
    client.post(f"/customer/enquiries/{enquiry.id}/reply", content_type="multipart/form-data", data={
        "message": "", "attachments": [(BytesIO(png_bytes()), "kitchen.png")]})
    photo_reply = enquiry.replies[1]
    assert photo_reply.message == "" and photo_reply.attachments[0].content_type == "image/png"
    assert "Sent 1 file" in client.get("/customer/enquiries").get_data(as_text=True)
    client.get("/logout")

    login(client, "des@test.com")
    assert client.get(f"/designer/enquiries/attachments/{photo_reply.attachments[0].id}").status_code == 200
    # The first message's files and each reply's files stay separate
    assert enquiry.attachments == [] and [len(m.attachments) for m in enquiry.conversation] == [0, 1, 1]


def test_reply_needs_text_or_a_file_and_bad_files_are_rejected(app):
    from app.control.reply_to_enquiry_controller import ReplyToEnquiryController

    designer, customer = people()
    SendEnquiryController().send(customer.id, designer.id, "Sam", "cus@test.com", "Hi")
    enquiry = Enquiry.query.one()
    with pytest.raises(ValueError, match="write a reply or attach a file"):
        ReplyToEnquiryController().reply(designer.id, enquiry.id, "  ")
    with pytest.raises(ValueError, match="Only JPG, PNG and PDF"):
        ReplyToEnquiryController().reply(designer.id, enquiry.id, "See file", [Upload("x.exe", b"MZ")])
    assert enquiry.replies == [] and EnquiryAttachment.query.count() == 0


def test_older_database_gets_the_reply_column_added(app):
    db.session.remove()
    with db.engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE enquiry_attachment")
        connection.exec_driver_sql(
            "CREATE TABLE enquiry_attachment (id INTEGER PRIMARY KEY, enquiry_id INTEGER NOT NULL, "
            "filename VARCHAR(255) NOT NULL, content_type VARCHAR(30) NOT NULL, size INTEGER NOT NULL, "
            "data BLOB NOT NULL)")
    EnquiryAttachment.ensure_schema()
    EnquiryAttachment.ensure_schema()  # running it again is harmless
    columns = {c["name"] for c in db.inspect(db.engine).get_columns("enquiry_attachment")}
    assert "reply_id" in columns
