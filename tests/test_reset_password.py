"""UA-16: User Admin resets a user's password."""
from app.control.change_password_controller import ChangePasswordController
from app.control.login_controller import LoginController
from app.control.reset_password_controller import ResetPasswordController
from app.entity.user_account import UserAccount


def make_user():
    return UserAccount.create("cus@test.com", "password123", "customer", name="Cus")


def test_reset_gives_a_new_temporary_password_and_old_one_stops_working(app):
    account = make_user()
    temporary = ResetPasswordController().reset(account.id)
    assert len(temporary) == ResetPasswordController.LENGTH
    assert LoginController().login("cus@test.com", "password123") is None
    assert LoginController().login("cus@test.com", temporary) == account


def test_each_reset_is_different(app):
    account = make_user()
    assert ResetPasswordController().reset(account.id) != ResetPasswordController().reset(account.id)


def test_user_must_change_the_temporary_password(app):
    account = make_user()
    temporary = ResetPasswordController().reset(account.id)
    assert ResetPasswordController().must_change_password(account.id)
    ChangePasswordController().change(account.id, temporary, "mynewpass1", "mynewpass1")
    assert not ResetPasswordController().must_change_password(account.id)


def test_only_a_hash_is_stored_so_the_admin_never_sees_passwords(app):
    account = make_user()
    temporary = ResetPasswordController().reset(account.id)
    assert temporary not in account.password_hash
    assert account.password_hash.startswith("scrypt:")
