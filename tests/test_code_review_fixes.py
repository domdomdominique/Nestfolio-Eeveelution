import io
from datetime import datetime, timedelta

import pytest
from PIL import Image
from sqlalchemy import event
from werkzeug.datastructures import FileStorage

from app.control.enquiry_attachment_validation import validated_attachments
from app.control.portfolio_validation import validated_photos
from app.entity.db import db
from app.entity.enquiry import Enquiry
from app.entity.reply import Reply
from app.entity.user_account import UserAccount


def png_bytes():
    out = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(out, "PNG")
    return out.getvalue()


def test_file_names_with_non_ascii_letters_keep_their_extension():
    pdf = FileStorage(io.BytesIO(b"%PDF-1.4 x"), filename="报告.pdf")
    assert validated_attachments([pdf])[0]["filename"].endswith(".pdf")
    photo = FileStorage(io.BytesIO(png_bytes()), filename="图.PNG")
    assert validated_photos([photo])[0]["filename"].endswith(".png")


def test_other_file_types_are_still_refused():
    exe = FileStorage(io.BytesIO(b"MZ"), filename="报告.exe")
    try:
        validated_attachments([exe])
    except ValueError as error:
        assert "Only JPG, PNG and PDF" in str(error)
    else:
        raise AssertionError("an .exe must be refused")


def queries_for_one_page(app, conversations):
    des = UserAccount.create(f"d{conversations}@test.com", "password123", "designer", name="Des",
                             phone=f"9{conversations:07d}")
    cus = UserAccount.create(f"c{conversations}@test.com", "password123", "customer", name="Cus",
                             phone=f"8{conversations:07d}")
    for i in range(conversations):
        enquiry = Enquiry.send(des.id, cus.id, "Cus", "c@test.com", f"hello {i}")
        Reply.add(enquiry, des.id, "reply")
    client = app.test_client()
    client.post("/login", data={"email": f"d{conversations}@test.com", "password": "password123"})
    count = []
    listener = lambda *args: count.append(1)  # noqa: E731
    event.listen(db.engine, "before_cursor_execute", listener)
    try:
        assert client.get("/designer/enquiries").status_code == 200
    finally:
        event.remove(db.engine, "before_cursor_execute", listener)
    return len(count)


def test_enquiry_pages_do_not_run_a_query_per_conversation(app):
    few = queries_for_one_page(app, 3)
    many = queries_for_one_page(app, 30)
    assert many == few, f"{few} queries for 3 conversations but {many} for 30"


# --- Two requests at once must not give a 500 page -------------------------------------

def test_a_lost_sign_up_race_gives_a_message_not_a_crash(app):
    UserAccount.create("a@test.com", "password123", "customer", name="A", phone="81112222")
    # The "is it taken?" check can pass for both requests; the unique index then stops the second one.
    with pytest.raises(ValueError, match="Email already registered"):
        UserAccount.create("a@test.com", "password123", "customer", name="B", phone="83334444")
    with pytest.raises(ValueError, match="Phone number already registered"):
        UserAccount.create("b@test.com", "password123", "customer", name="B", phone="81112222")
    assert UserAccount.query.count() == 1  # nothing half-saved


def test_opening_a_new_conversation_twice_at_once_does_not_crash(tmp_path):
    from app import create_app
    from app.entity.reply import EnquirySeen

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'race.db'}"})
    with app.app_context():
        des = UserAccount.create("d@test.com", "password123", "designer", name="D", phone="91234567")
        cus = UserAccount.create("c@test.com", "password123", "customer", name="C", phone="81112222")
        eid = Enquiry.send(des.id, cus.id, "C", "c@test.com", "hi").id
        did = des.id

        def another_request_wins(session, context, instances):
            with db.engine.begin() as other:  # a second request records the first visit just before us
                other.exec_driver_sql("INSERT INTO enquiry_seen (enquiry_id, user_id, seen_at) VALUES (?, ?, '2020-01-01')",
                                      (eid, did))

        event.listen(db.session, "before_flush", another_request_wins, once=True)
        EnquirySeen.mark([eid], did)  # used to raise IntegrityError
        rows = EnquirySeen.query.filter_by(enquiry_id=eid, user_id=did).all()
        assert len(rows) == 1 and rows[0].seen_at.year > 2020  # still one row, with our later time


# --- The unread badge is counted in the database, with the same answer as the Python rule ------

def test_the_sql_unread_count_matches_the_rule_used_by_the_inbox(app):
    from app.entity.reply import EnquirySeen
    from app.control.enquiry_notification_controller import EnquiryNotificationController

    des = UserAccount.create("d@test.com", "password123", "designer", name="D", phone="91234567")
    cus = [UserAccount.create(f"c{i}@test.com", "password123", "customer", name=f"C{i}", phone=f"8111222{i}")
           for i in range(3)]
    base = datetime(2026, 1, 1, 12, 0)
    for i, customer in enumerate(cus):
        for j in range(4):  # a mix: never opened, opened since, replied to, answered back after opening
            enquiry = Enquiry.send(des.id, customer.id, "n", "c@test.com", f"m{i}{j}")
            enquiry.created_at = base + timedelta(hours=j)
            reply_at = base + timedelta(hours=j, minutes=30)
            if j >= 1:
                reply = Reply.add(enquiry, des.id, "designer reply")
                reply.created_at = reply_at
            if j == 3:
                reply = Reply.add(enquiry, customer.id, "customer answer")
                reply.created_at = reply_at + timedelta(minutes=10)
            if j in (2, 3):
                db.session.add(EnquirySeen(enquiry_id=enquiry.id, user_id=des.id, seen_at=reply_at + timedelta(minutes=5)))
                db.session.add(EnquirySeen(enquiry_id=enquiry.id, user_id=customer.id, seen_at=reply_at + timedelta(minutes=1)))
    db.session.commit()

    controller = EnquiryNotificationController()
    for person in [des] + cus:
        mine = Enquiry.query.filter((Enquiry.designer_id == person.id) | (Enquiry.customer_id == person.id)).all()
        by_python = sum(1 for n in controller.unread_by_enquiry(person.id, mine).values() if n)
        assert Enquiry.unread_count_for(person.id) == by_python, person.email
    assert Enquiry.unread_count_for(des.id) > 0 and Enquiry.unread_count_for(cus[0].id) > 0  # not a trivial 0 == 0


def test_a_page_that_is_not_about_enquiries_costs_the_same_with_many_conversations(app):
    def queries(conversations):
        des = UserAccount.create(f"p{conversations}@test.com", "password123", "designer", name="P",
                                 phone=f"9{conversations + 100:07d}")
        cus = UserAccount.create(f"q{conversations}@test.com", "password123", "customer", name="Q",
                                 phone=f"8{conversations + 100:07d}")
        for i in range(conversations):
            Reply.add(Enquiry.send(des.id, cus.id, "Q", "q@test.com", f"hi {i}"), cus.id, "again")
        client = app.test_client()
        client.post("/login", data={"email": f"p{conversations}@test.com", "password": "password123"})
        count = []
        listener = lambda *args: count.append(1)  # noqa: E731
        event.listen(db.engine, "before_cursor_execute", listener)
        try:
            assert client.get("/designer/portfolio").status_code == 200
        finally:
            event.remove(db.engine, "before_cursor_execute", listener)
        return len(count)

    assert queries(40) == queries(2)


# --- Several workers starting at once, and SQLite under several workers ----------------------

def test_start_up_carries_on_when_another_worker_set_up_the_database_first(tmp_path):
    from sqlalchemy.exc import OperationalError

    from app import create_app

    uri = f"sqlite:///{tmp_path / 'boot.db'}"
    create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": uri})  # worker 1 sets everything up
    real = db.create_all
    calls = []

    def lost_the_race(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise OperationalError("CREATE TABLE enquiry", {}, Exception("table enquiry already exists"))
        return real(*args, **kwargs)

    db.create_all = lost_the_race
    try:
        app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": uri})  # worker 2 loses the race once
    finally:
        db.create_all = real
    assert app is not None and len(calls) == 2  # it looked again and carried on


def test_sqlite_waits_for_a_busy_file_and_uses_wal(tmp_path):
    from app import create_app

    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'wal.db'}"})
    with app.app_context():
        assert db.session.execute(db.text("PRAGMA journal_mode")).scalar() == "wal"
        assert db.session.execute(db.text("PRAGMA busy_timeout")).scalar() == 15000


# --- Days follow Singapore time, not the server's clock --------------------------------------

@pytest.mark.skipif(not hasattr(__import__("time"), "tzset"), reason="Windows uses the PC's own time zone setting")
def test_now_is_singapore_time_even_on_a_utc_server(monkeypatch):
    from zoneinfo import ZoneInfo

    from app import create_app

    monkeypatch.setenv("TZ", "UTC")  # what a cloud host looks like before the app starts
    monkeypatch.delenv("APP_TIMEZONE", raising=False)
    create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    singapore = datetime.now(ZoneInfo("Asia/Singapore")).replace(tzinfo=None)
    assert abs((datetime.now() - singapore).total_seconds()) < 5


# --- Edge cases found while reviewing the fixes -----------------------------------------------

def test_file_names_with_stray_spaces_still_work():
    pdf = FileStorage(io.BytesIO(b"%PDF-1.4 x"), filename="  Quote 2026.PDF ")
    assert validated_attachments([pdf])[0]["filename"] == "Quote_2026.pdf"


def test_only_a_unique_clash_is_turned_into_a_message(app):
    from sqlalchemy.exc import IntegrityError

    def clash(message):
        def view():
            raise IntegrityError("INSERT ...", {}, Exception(message))
        return view

    app.add_url_rule("/unique-clash", "unique_clash", clash("UNIQUE constraint failed: user_account.email"))
    app.add_url_rule("/other-bug", "other_bug", clash("NOT NULL constraint failed: user_account.name"))
    client = app.test_client()
    assert client.get("/unique-clash").status_code == 302  # a message and a redirect
    with pytest.raises(IntegrityError):  # a real bug must not be hidden behind that message
        client.get("/other-bug")


def test_create_account_does_not_mislabel_an_unrelated_integrity_error(app, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    def broken_commit():
        raise IntegrityError("INSERT ...", {}, Exception("NOT NULL constraint failed: user_account.name"))

    monkeypatch.setattr(db.session, "commit", broken_commit)
    with pytest.raises(IntegrityError):
        UserAccount.create("x@test.com", "password123", "customer", name="X", phone="81112222")


def test_marking_seen_leaves_the_session_setting_as_it_was(app):
    from app.entity.reply import EnquirySeen

    des = UserAccount.create("d@test.com", "password123", "designer", name="D", phone="91234567")
    cus = UserAccount.create("c@test.com", "password123", "customer", name="C", phone="81112222")
    enquiry = Enquiry.send(des.id, cus.id, "C", "c@test.com", "hi")
    EnquirySeen.mark([enquiry.id], des.id)
    assert db.session().expire_on_commit is True


def test_several_processes_starting_together_on_a_new_database_all_succeed(tmp_path):
    """The real thing behind the start-up retry and the SQLite settings: Gunicorn workers booting at once."""
    import subprocess
    import sys

    code = ("import sys\nfrom app import create_app\n"
            "create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + sys.argv[1]})\nprint('ok')")
    path = str(tmp_path / "shared.db")
    workers = [subprocess.Popen([sys.executable, "-c", code, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True) for _ in range(6)]
    results = [(w.wait(timeout=120), w.stdout.read(), w.stderr.read()) for w in workers]
    failed = [r for r in results if r[0] != 0 or "ok" not in r[1]]
    assert not failed, failed[0][2][-600:]
