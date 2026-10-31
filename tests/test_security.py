"""Security checklist: visitors and wrong roles are kept out, CSRF is enforced, personal data is protected."""
import re
import sqlite3

import pytest

from app import create_app
from app.entity.db import db
from app.entity.user_account import UserAccount

PRIVATE_PREFIXES = ("/admin", "/platform", "/designer")


def private_urls(app):
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith(PRIVATE_PREFIXES):
            yield rule, re.sub(r"<[^>]+>", "1", rule.rule)


def test_visitor_cannot_open_any_admin_platform_or_designer_page(client, app):
    checked = 0
    for rule, url in private_urls(app):
        for method in rule.methods & {"GET", "POST"}:
            response = client.open(url, method=method)
            assert response.status_code == 302 and "/login" in response.headers["Location"], (method, url)
            checked += 1
    assert checked > 40  # really did walk the routes


@pytest.mark.parametrize("role, allowed", [("customer", None), ("designer", "/designer"),
                                           ("platform", "/platform"), ("admin", "/admin")])
def test_a_role_only_opens_its_own_area(client, app, role, allowed):
    UserAccount.create(f"{role}@test.com", "password123", role)
    client.post("/login", data={"email": f"{role}@test.com", "password": "password123"})
    for rule, url in private_urls(app):
        if "GET" in rule.methods and not (allowed and rule.rule.startswith(allowed)):
            assert client.get(url).status_code == 403, (role, url)


def test_suspended_account_is_logged_out_on_the_next_request(client, app):
    account = UserAccount.create("des@test.com", "password123", "designer")
    client.post("/login", data={"email": "des@test.com", "password": "password123"})
    assert client.get("/designer/").status_code == 200
    account.is_suspended = True
    db.session.commit()
    assert client.get("/designer/").status_code == 302


@pytest.fixture
def csrf_client(tmp_path):
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": True,
                      "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 't.db'}"})
    with app.app_context():
        db.create_all()
        UserAccount.create("cus@test.com", "password123", "customer", name="Sam", phone="+65 91234567")
        yield app.test_client(), app, tmp_path / "t.db"
        db.session.remove()
        db.drop_all()


def test_posts_without_a_csrf_token_are_rejected(csrf_client):
    client, _, _ = csrf_client
    assert client.post("/login", data={"email": "cus@test.com", "password": "password123"}).status_code == 400
    page = client.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    ok = client.post("/login", data={"email": "cus@test.com", "password": "password123", "csrf_token": token})
    assert ok.status_code == 302


def test_database_file_holds_no_plain_passwords_or_phone_numbers(csrf_client):
    _, _, path = csrf_client
    raw = sqlite3.connect(path).execute("select password_hash, phone, phone_hash from user_account").fetchone()
    assert all("password123" not in v and "91234567" not in v for v in raw)
    assert raw[0].startswith(("scrypt:", "pbkdf2:")) and raw[1].startswith("gAAAA")  # hash / Fernet token


def test_login_does_not_reveal_whether_an_email_exists(client, app):
    UserAccount.create("cus@test.com", "password123", "customer")
    known = client.post("/login", data={"email": "cus@test.com", "password": "wrong"}).get_data(as_text=True)
    unknown = client.post("/login", data={"email": "nobody@test.com", "password": "wrong"}).get_data(as_text=True)
    assert "Invalid email or password." in known and "Invalid email or password." in unknown


def test_enquiry_contact_is_encrypted_in_the_database(csrf_client):
    from app.entity.enquiry import Enquiry
    _, _, path = csrf_client
    designer = UserAccount.create("des@test.com", "password123", "designer")
    customer = UserAccount.query.filter_by(email="cus@test.com").one()
    Enquiry.send(designer.id, customer.id, "Sam", "+65 91234567", "Hello")
    assert Enquiry.query.one().contact == "+65 91234567"  # plain in Python
    assert "91234567" not in sqlite3.connect(path).execute("select contact from enquiry").fetchone()[0]


def test_secrets_come_from_env_or_a_generated_file_never_from_the_source(tmp_path, monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    from app import _load_secret
    app = SimpleNamespace(instance_path=str(tmp_path))
    monkeypatch.delenv("SECRET_KEY", raising=False)
    first = _load_secret(app, "SECRET_KEY", lambda: "generated-once")
    assert first == "generated-once" and _load_secret(app, "SECRET_KEY", lambda: "other") == first  # kept
    assert (tmp_path / "secret_key.key").stat().st_mode & 0o077 == 0  # owner-only
    monkeypatch.setenv("SECRET_KEY", "from-env")
    assert _load_secret(app, "SECRET_KEY", lambda: "x") == "from-env"
    source = (Path(__file__).parent.parent / "app" / "__init__.py").read_text()
    assert "dev-change-me" not in source and "1dCtVD" not in source
    assert "debug=True" not in (Path(__file__).parent.parent / "run.py").read_text()
