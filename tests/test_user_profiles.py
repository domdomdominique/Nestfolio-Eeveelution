"""UA-08 to UA-12: User Admin manages user profiles (roles)."""
import pytest

from app.control.create_user_account_controller import CreateUserAccountController
from app.control.create_user_profile_controller import CreateUserProfileController
from app.control.login_controller import LoginController
from app.control.search_user_profile_controller import SearchUserProfileController
from app.control.suspend_user_profile_controller import SuspendUserProfileController
from app.control.update_user_profile_controller import UpdateUserProfileController
from app.control.view_user_profile_controller import ViewUserProfileController
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile


def test_the_four_actor_profiles_exist(app):
    assert [p.key for p in ViewUserProfileController().list_profiles()] == ["admin", "platform", "designer", "customer"]


# --- UA-08 Create -------------------------------------------------------------

def test_new_profile_is_active_and_can_be_assigned(app):
    profile = CreateUserProfileController().create(" Contractor ", "Renovation contractors")
    assert (profile.name, profile.status, profile.key) == ("Contractor", "active", "contractor")
    account = CreateUserAccountController().create("Ah Seng", "seng@test.com", "91112222", "password123", profile.key)
    assert account.profile_name == "Contractor"


def test_profiles_with_similar_names_get_different_keys(app):
    first = CreateUserProfileController().create("Site Manager")
    second = CreateUserProfileController().create("Site-Manager")
    assert first.key != second.key


@pytest.mark.parametrize("name, message", [("", "Please enter a profile name"),
                                           ("customer", "already exists"),
                                           ("x" * 51, "50 characters")])
def test_missing_or_duplicate_name_saves_nothing(app, name, message):
    with pytest.raises(ValueError, match=message):
        CreateUserProfileController().create(name)
    assert UserProfile.query.count() == 4


# --- UA-09 View ---------------------------------------------------------------

def test_view_shows_status_and_number_of_accounts(app):
    UserAccount.create("a@test.com", "password123", "customer")
    UserAccount.create("b@test.com", "password123", "customer")
    customer = next(p for p in ViewUserProfileController().list_profiles() if p.key == "customer")
    assert (customer.name, customer.status, customer.account_count) == ("Customer", "active", 2)
    assert ViewUserProfileController().view(customer.id).description


def test_view_missing_profile(app):
    with pytest.raises(LookupError):
        ViewUserProfileController().view(999)


# --- UA-10 Update -------------------------------------------------------------

def test_rename_shows_on_accounts_using_it(app):
    account = UserAccount.create("a@test.com", "password123", "customer")
    customer = UserProfile.by_key("customer")
    UpdateUserProfileController().update(customer.id, "Home Owner", "People renovating")
    assert account.profile_name == "Home Owner"
    assert account.role == "customer"  # pages and permissions keep working


@pytest.mark.parametrize("name", ["", "User Admin"])
def test_update_with_empty_or_duplicate_name_saves_nothing(app, name):
    customer = UserProfile.by_key("customer")
    with pytest.raises(ValueError):
        UpdateUserProfileController().update(customer.id, name)
    assert UserProfile.by_key("customer").name == "Customer"


# --- UA-11 Suspend ------------------------------------------------------------

def test_suspended_profile_blocks_login_of_its_accounts(app):
    UserAccount.create("des@test.com", "password123", "designer")
    SuspendUserProfileController().suspend(UserProfile.by_key("designer").id)
    assert UserProfile.by_key("designer").status == "suspended"
    assert LoginController().login("des@test.com", "password123") is None
    assert "suspended" in LoginController().failure_message("des@test.com", "password123")


def test_suspended_profile_cannot_be_given_to_new_accounts(app):
    SuspendUserProfileController().suspend(UserProfile.by_key("designer").id)
    assert "designer" not in [p.key for p in UserProfile.active()]
    with pytest.raises(ValueError, match="suspended"):
        CreateUserAccountController().create("Des", "des@test.com", "91112222", "password123", "designer")


def test_user_admin_profile_can_never_be_suspended(app):
    with pytest.raises(ValueError, match="cannot be suspended"):
        SuspendUserProfileController().suspend(UserProfile.by_key("admin").id)
    assert UserProfile.by_key("admin").status == "active"


# --- UA-12 Search -------------------------------------------------------------

def test_search_profiles_by_name(app):
    assert [p.name for p in SearchUserProfileController().search("admin")] == ["User Admin"]
    assert [p.key for p in SearchUserProfileController().search("  ")] == ["admin", "platform", "designer", "customer"]


def test_search_with_no_matches_returns_nothing(app):
    assert SearchUserProfileController().search("zzzz") == []


def test_suspending_a_profile_logs_out_its_users(client, app):
    UserAccount.create("des@test.com", "password123", "designer")
    client.post("/login", data={"email": "des@test.com", "password": "password123"})
    assert client.get("/designer/").status_code == 200
    SuspendUserProfileController().suspend(UserProfile.by_key("designer").id)
    assert client.get("/designer/").status_code == 302  # back to the login page
