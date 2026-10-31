"""Designer's own profile: ID-17 view, ID-18 edit. Also checks CSRF protection is on."""
import pytest

from app import create_app
from app.control.update_designer_profile_controller import UpdateDesignerProfileController
from app.entity.db import db as _db
from app.entity.user_account import UserAccount


@pytest.fixture
def designer(app):
    return UserAccount.create("des@test.com", "password123", "designer",
                              name="Dana Ong", phone="+65 91234567")


def login(client, email="des@test.com"):
    client.post("/login", data={"email": email, "password": "password123"})


def test_profile_shows_details_status_and_never_the_password(client, designer):
    login(client)
    html = client.get("/designer/profile").get_data(as_text=True)
    assert "Dana Ong" in html and "des@test.com" in html and "+65" in html and "91234567" in html
    assert "Registration approved" in html
    assert "password123" not in html and designer.password_hash not in html


def test_profile_is_only_for_designers(client, designer):
    UserAccount.create("cus@test.com", "password123", "customer", name="Sam")
    assert client.get("/designer/profile").status_code == 302
    login(client, "cus@test.com")
    assert client.get("/designer/profile").status_code == 403


def test_update_saves_valid_changes_and_refreshes_session_name(client, designer):
    login(client)
    response = client.post("/designer/profile", data={
        "name": "Dana Lim", "email": "dana@test.com", "phone": "9876 5432",
        "current_password": "password123"})
    assert response.status_code == 302
    account = UserAccount.get(designer.id)
    assert (account.name, account.email, account.phone) == ("Dana Lim", "dana@test.com", "+65 98765432")
    assert "Dana Lim" in client.get("/designer/profile?updated=1").get_data(as_text=True)


@pytest.mark.parametrize("data", [
    {"name": "", "email": "a@b.co", "phone": "91234567"},
    {"name": "Dana", "email": "not-an-email", "phone": "91234567"},
    {"name": "Dana", "email": "a@b.co", "phone": "123"},
])
def test_invalid_update_changes_nothing_and_shows_error(client, designer, data):
    login(client)
    response = client.post("/designer/profile", data={**data, "current_password": "password123"})
    assert response.status_code == 200
    assert 'role="alert"' in response.get_data(as_text=True)
    assert UserAccount.get(designer.id).email == "des@test.com"


def test_email_used_by_another_account_is_refused(designer):
    UserAccount.create("taken@test.com", "password123", "customer", name="Sam")
    with pytest.raises(ValueError):
        UpdateDesignerProfileController().update(designer.id, "Dana", "taken@test.com", "91234567", "password123")


def test_unchanged_email_is_allowed(designer):
    UpdateDesignerProfileController().update(designer.id, "Dana", "des@test.com", "91234567", "password123")


def test_forged_post_without_csrf_token_is_rejected():
    """The shared test config switches CSRF off; here it is on, as in production."""
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        UserAccount.create("des@test.com", "password123", "designer", name="Dana")
        client = app.test_client()
        assert client.post("/login", data={"email": "des@test.com", "password": "password123"}).status_code == 400
        _db.drop_all()
