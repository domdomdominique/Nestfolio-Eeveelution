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
        "company_name": "Dana Lim", "email": "dana@test.com", "phone": "9876 5432",
        "current_password": "password123"})
    assert response.status_code == 302
    account = UserAccount.get(designer.id)
    assert (account.name, account.email, account.phone) == ("Dana Lim", "dana@test.com", "+65 98765432")
    assert "Dana Lim" in client.get("/designer/profile?updated=1").get_data(as_text=True)


@pytest.mark.parametrize("data", [
    {"company_name": "", "email": "a@b.co", "phone": "91234567"},
    {"company_name": "Dana", "email": "not-an-email", "phone": "91234567"},
    {"company_name": "Dana", "email": "a@b.co", "phone": "123"},
    {"company_name": "Dana", "email": "a@b.co", "phone": "91234567", "experience_years": "-1"},
    {"company_name": "Dana", "email": "a@b.co", "phone": "91234567", "portfolio_url": "oak.sg"},
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


def test_profile_shows_company_information_not_personal_details(client, designer):
    login(client)
    html = client.get("/designer/profile").get_data(as_text=True)
    assert "Company information" in html and "Personal details" not in html
    for field in ("company_name", "email", "phone", "experience_years", "portfolio_url", "description"):
        assert f'name="{field}"' in html
    assert 'name="name"' not in html and "Full name" not in html


def test_saving_company_information_updates_account_and_company(client, designer):
    from app.entity.designer_company import DesignerCompany
    login(client)
    client.post("/designer/profile", data={
        "company_name": "Oak Studio", "email": "oakstudio@test.com", "phone": "9123 4567",
        "experience_years": "7", "portfolio_url": "https://oak.sg", "description": "Warm homes.",
        "current_password": "password123"})
    account = UserAccount.get(designer.id)
    assert (account.name, account.email) == ("Oak Studio", "oakstudio@test.com")
    company = DesignerCompany.for_account(designer.id)
    assert (company.company_name, company.experience_years, company.portfolio_url, company.description) == \
        ("Oak Studio", 7, "https://oak.sg", "Warm homes.")
    page = client.get(f"/customer/designers/{designer.id}").get_data(as_text=True)
    assert "Oak Studio" in page and "Warm homes." in page and "oak.sg" in page
