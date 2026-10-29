"""UA-01, UA-03 to UA-07 and UA-13: User Admin manages user accounts."""
import pytest

from app.control.create_user_account_controller import CreateUserAccountController
from app.control.login_controller import LoginController
from app.control.reactivate_user_account_controller import ReactivateUserAccountController
from app.control.search_user_account_controller import SearchUserAccountController
from app.control.suspend_user_account_controller import SuspendUserAccountController
from app.control.update_user_account_controller import UpdateUserAccountController
from app.control.view_user_account_controller import ViewUserAccountController
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile

GOOD = dict(name="Wei Ming Tan", email="weiming@test.com", phone="9123 4567",
            password="password123", role="customer")


def make_admin():
    return UserAccount.create("admin@test.com", "password123", "admin", name="Admin")


# --- UA-01 suspended login message ------------------------------------------

def test_suspended_account_gets_suspended_message_only_with_right_password(app):
    account = CreateUserAccountController().create(**GOOD)
    account.set_suspended(True)
    assert "suspended" in LoginController().failure_message("weiming@test.com", "password123")
    assert LoginController().failure_message("weiming@test.com", "wrongpass") == "Invalid email or password."
    assert LoginController().login("weiming@test.com", "password123") is None


# --- UA-03 Create -------------------------------------------------------------

def test_created_account_is_active_and_can_log_in(app):
    account = CreateUserAccountController().create(**GOOD)
    assert (account.status, account.phone, account.role) == ("Active", "+65 91234567", "customer")
    assert LoginController().login("weiming@test.com", "password123") == account


def test_profile_choices_include_new_profiles(app):
    UserProfile.create("Contractor")
    assert ("contractor", "Contractor") in SearchUserAccountController().profile_choices()
    assert CreateUserAccountController().create(**{**GOOD, "role": "contractor"}).profile_name == "Contractor"


@pytest.mark.parametrize("changes, message", [
    ({"name": ""}, "name"),
    ({"email": "not-an-email"}, "valid email"),
    ({"phone": "123"}, "phone"),
    ({"password": "short"}, "at least 8"),
    ({"role": "nobody"}, "choose a user profile"),
])
def test_missing_or_invalid_fields_create_nothing(app, changes, message):
    with pytest.raises(ValueError, match=message):
        CreateUserAccountController().create(**{**GOOD, **changes})
    assert not UserAccount.email_exists("weiming@test.com")


def test_email_or_phone_already_in_use_is_rejected(app):
    CreateUserAccountController().create(**GOOD)
    with pytest.raises(ValueError, match="Email already registered"):
        CreateUserAccountController().create(**{**GOOD, "phone": "81234567"})
    with pytest.raises(ValueError, match="Phone number already registered"):
        CreateUserAccountController().create(**{**GOOD, "email": "other@test.com"})


def test_suspended_profile_cannot_be_chosen(app):
    designer = UserProfile.by_key("designer")
    designer.suspend()
    with pytest.raises(ValueError, match="suspended"):
        CreateUserAccountController().create(**{**GOOD, "role": "designer"})


# --- UA-04 View ---------------------------------------------------------------

def test_view_shows_details_but_never_the_password(app):
    account = CreateUserAccountController().create(**GOOD)
    details = ViewUserAccountController().view(account.id)
    assert details["name"] == "Wei Ming Tan" and details["phone"] == "+65 91234567"
    assert details["profile"] == "Customer" and details["status"] == "Active"
    assert details["created_at"] is not None
    assert not any("password" in key and key != "must_change_password" for key in details)
    assert account.password_hash not in details.values()


def test_view_missing_account(app):
    with pytest.raises(LookupError):
        ViewUserAccountController().view(999)


# --- UA-05 Update -------------------------------------------------------------

def test_update_saves_changes_shown_on_view(app):
    account = CreateUserAccountController().create(**GOOD)
    UpdateUserAccountController().update(account.id, "Wei Ming Lim", "WM@Test.com", "+65 8888 1234", "designer")
    details = ViewUserAccountController().view(account.id)
    assert (details["name"], details["email"], details["phone"], details["profile"]) == \
        ("Wei Ming Lim", "wm@test.com", "+65 88881234", "Interior Designer")


def test_keeping_own_email_and_phone_is_allowed(app):
    account = CreateUserAccountController().create(**GOOD)
    UpdateUserAccountController().update(account.id, "New Name", GOOD["email"], GOOD["phone"], "customer")
    assert account.name == "New Name"


def test_update_with_another_accounts_email_saves_nothing(app):
    account = CreateUserAccountController().create(**GOOD)
    CreateUserAccountController().create(**{**GOOD, "email": "taken@test.com", "phone": "81111111"})
    with pytest.raises(ValueError, match="Email already registered"):
        UpdateUserAccountController().update(account.id, "Changed", "taken@test.com", GOOD["phone"], "customer")
    assert UserAccount.get(account.id).name == "Wei Ming Tan"


def test_update_with_invalid_field_saves_nothing(app):
    account = CreateUserAccountController().create(**GOOD)
    with pytest.raises(ValueError):
        UpdateUserAccountController().update(account.id, "", GOOD["email"], GOOD["phone"], "customer")
    assert UserAccount.get(account.id).name == "Wei Ming Tan"


# --- UA-06 Suspend / UA-13 Reactivate -------------------------------------------

def test_suspend_keeps_data_and_blocks_login(app):
    admin = make_admin()
    account = CreateUserAccountController().create(**GOOD)
    SuspendUserAccountController().suspend(admin.id, account.id)
    assert UserAccount.get(account.id).status == "Suspended"
    assert UserAccount.get(account.id).email == "weiming@test.com"  # kept, not deleted
    assert LoginController().login("weiming@test.com", "password123") is None


def test_admin_cannot_suspend_own_account(app):
    admin = make_admin()
    with pytest.raises(ValueError, match="your own account"):
        SuspendUserAccountController().suspend(admin.id, admin.id)
    assert not admin.is_suspended


def test_reactivate_lets_user_log_in_again(app):
    admin = make_admin()
    account = CreateUserAccountController().create(**GOOD)
    SuspendUserAccountController().suspend(admin.id, account.id)
    ReactivateUserAccountController().reactivate(account.id)
    assert account.status == "Active"
    assert LoginController().login("weiming@test.com", "password123") == account


def test_only_suspended_accounts_can_be_reactivated(app):
    account = CreateUserAccountController().create(**GOOD)
    with pytest.raises(ValueError, match="Only suspended"):
        ReactivateUserAccountController().reactivate(account.id)


# --- UA-07 Search -------------------------------------------------------------

def setup_accounts():
    admin = make_admin()
    a = CreateUserAccountController().create(**GOOD)
    b = CreateUserAccountController().create(name="Priya Nair", email="priya@test.com",
                                             phone="82222222", password="password123", role="designer")
    SuspendUserAccountController().suspend(admin.id, b.id)
    return a, b


def test_search_by_name_or_email(app):
    a, b = setup_accounts()
    assert SearchUserAccountController().search("wei ming") == [a]
    assert SearchUserAccountController().search("PRIYA@") == [b]


def test_search_filters_by_profile_and_status(app):
    a, b = setup_accounts()
    controller = SearchUserAccountController()
    assert controller.search("test.com", role="designer") == [b]
    assert controller.search("test.com", status="active") == [UserAccount.query.filter_by(role="admin").first(), a]
    assert controller.search(status="suspended") == [b]
    assert controller.search(role="made-up") == controller.search()  # unknown filter ignored


def test_search_with_no_matches_returns_nothing(app):
    setup_accounts()
    assert SearchUserAccountController().search("zzzz") == []
