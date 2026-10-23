"""A login cookie is only honoured while it still matches a real, active account of that role.

Fixes the 'always logged in as Demo account' report: after the database was reseeded,
an old cookie for user id 1 (the demo account) kept working.
"""
from app.control.validate_session_controller import ValidateSessionController
from app.entity.db import db
from app.entity.user_account import UserAccount


def make(role="designer", email="des@test.com"):
    return UserAccount.create(email, "password123", role, name="Dana Ong")


def set_session(client, user_id, role, token="old-token"):
    with client.session_transaction() as s:
        s["user_id"], s["role"], s["name"], s["auth"] = user_id, role, "Dana", token


def test_controller_accepts_only_matching_active_accounts(app):
    account = make()
    controller = ValidateSessionController()
    token = controller.token_for(account)
    check = controller.is_valid
    assert check(account.id, "designer", token) is True
    assert check(account.id, "admin", token) is False       # role in cookie does not match the account
    assert check(9999, "designer", token) is False          # account no longer exists
    assert check(account.id, "designer", "forged") is False
    assert check(account.id, "designer", None) is False
    assert check(None, None, None) is False
    account.is_suspended = True
    db.session.commit()
    assert check(account.id, "designer", token) is False    # suspended while logged in


def test_cookie_for_a_missing_account_is_dropped(client, app):
    set_session(client, 1, "admin")                  # nothing in the database
    response = client.get("/designer/")
    assert response.status_code == 302 and "/login" in response.headers["Location"]
    with client.session_transaction() as s:
        assert "user_id" not in s


def test_public_pages_do_not_treat_a_stale_cookie_as_logged_in(client, app):
    set_session(client, 1, "customer")
    html = client.get("/").get_data(as_text=True)
    assert "Hi, Dana" not in html
    with client.session_transaction() as s:
        assert "user_id" not in s


def test_suspending_an_account_logs_it_out_on_the_next_request(client, app):
    account = make()
    client.post("/login", data={"email": "des@test.com", "password": "password123", "role": "designer"})
    assert client.get("/designer/").status_code == 200
    account.is_suspended = True
    db.session.commit()
    assert client.get("/designer/").status_code == 302


def test_valid_session_keeps_working(client, app):
    make()
    client.post("/login", data={"email": "des@test.com", "password": "password123", "role": "designer"})
    assert client.get("/designer/").status_code == 200
    assert client.get("/designer/portfolio").status_code == 200


def test_static_files_do_not_need_a_session_lookup(client, app):
    assert client.get("/static/css/site.css").status_code == 200


def test_cookie_from_before_a_reseed_is_dropped_even_if_the_ids_match(client, app):
    """The reported bug: the reseeded database has a new 'demo' account with the same id and role."""
    old = make("customer", "customer@demo.com")
    client.post("/login", data={"email": "customer@demo.com", "password": "password123", "role": "customer"})
    assert "Hi, Dana" in client.get("/").get_data(as_text=True)
    old_cookie_id = old.id
    db.session.remove()
    db.drop_all()
    db.create_all()                                   # what `python seed.py` does
    new = make("customer", "customer@demo.com")
    assert new.id == old_cookie_id                    # same id and role as before
    assert "Hi, Dana" not in client.get("/").get_data(as_text=True)
    assert client.get("/customer/favourites").status_code == 302


def test_changing_the_password_ends_other_sessions_but_not_this_one(client, app):
    make("customer", "cus@test.com")
    other = app.test_client()
    for c in (client, other):
        c.post("/login", data={"email": "cus@test.com", "password": "password123", "role": "customer"})
    client.post("/customer/profile/password", data={"current_password": "password123",
                                                    "new_password": "newpassword1", "confirm_password": "newpassword1"})
    assert client.get("/customer/profile").status_code == 200   # the browser that changed it stays in
    assert other.get("/customer/profile").status_code == 302    # any other browser is logged out
