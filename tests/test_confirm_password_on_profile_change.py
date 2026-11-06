"""Changing personal details needs the current password (C-12, ID-18 verification)."""
import pytest

from app.control.update_designer_profile_controller import UpdateDesignerProfileController
from app.control.update_profile_controller import UpdateProfileController
from app.entity.user_account import UserAccount


@pytest.fixture
def customer(app):
    return UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan", phone="+65 91234567")


@pytest.fixture
def designer(app):
    return UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong", phone="+65 81234567")


@pytest.mark.parametrize("password", ["", None, "wrong-password"])
def test_customer_update_needs_the_right_password(customer, password):
    with pytest.raises(ValueError, match="current password"):
        UpdateProfileController().update(customer.id, "New", "Name", "cus@test.com", "91234567", password)
    assert UserAccount.get(customer.id).name == "Sarah Tan"


def test_customer_update_works_with_the_right_password(customer):
    UpdateProfileController().update(customer.id, "New", "Name", "new@test.com", "91234567", "password123")
    assert UserAccount.get(customer.id).email == "new@test.com"


@pytest.mark.parametrize("password", ["", None, "wrong-password"])
def test_designer_update_needs_the_right_password(designer, password):
    with pytest.raises(ValueError, match="current password"):
        UpdateDesignerProfileController().update(designer.id, "New", "des@test.com", "81234567", password)
    assert UserAccount.get(designer.id).name == "Dana Ong"


def test_designer_update_works_with_the_right_password(designer):
    UpdateDesignerProfileController().update(designer.id, "Dana Lim", "des@test.com", "81234567", "password123")
    assert UserAccount.get(designer.id).name == "Dana Lim"


def test_pages_show_the_password_field_and_an_error_when_it_is_wrong(client, customer, designer):
    client.post("/login", data={"email": "des@test.com", "password": "password123", "role": "designer"})
    page = client.get("/designer/profile").get_data(as_text=True)
    assert 'name="current_password"' in page and 'type="password"' in page
    page = client.post("/designer/profile", data={"company_name": "X Y", "email": "des@test.com",
                                                   "phone": "81234567", "current_password": "nope"}).get_data(as_text=True)
    assert "current password" in page
    assert UserAccount.get(designer.id).name == "Dana Ong"
    client.get("/logout")
    client.post("/login", data={"email": "cus@test.com", "password": "password123", "role": "customer"})
    assert 'name="current_password"' in client.get("/customer/profile").get_data(as_text=True)


def test_password_is_never_echoed_back_after_an_error(client, designer):
    client.post("/login", data={"email": "des@test.com", "password": "password123", "role": "designer"})
    page = client.post("/designer/profile", data={"company_name": "X Y", "email": "des@test.com",
                                                   "phone": "81234567", "current_password": "secret-guess"}).get_data(as_text=True)
    assert "secret-guess" not in page
