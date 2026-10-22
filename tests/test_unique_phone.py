"""A phone number can belong to only one account (or one waiting designer application)."""
import pytest

from app.control.apply_designer_controller import ApplyDesignerController
from app.control.register_controller import RegisterController
from app.control.review_designer_application_controller import ReviewDesignerApplicationController
from app.control.update_designer_profile_controller import UpdateDesignerProfileController
from app.control.update_profile_controller import UpdateProfileController
from app.entity.db import db
from app.entity.user_account import UserAccount

PHONE = "+65 91234567"


def register(email="amy@test.com", phone="9123 4567"):
    return RegisterController().register("Amy Tan", email, phone, "password123", "password123")


def apply(email="ben@studio.com", phone="8765 4321"):
    return ApplyDesignerController().apply("Ben Lim", email, phone, "password123", "password123",
                                           "Ben Studio", "201912345K")


def test_customer_cannot_register_with_a_phone_already_in_use(app):
    register()
    with pytest.raises(ValueError, match="Phone number already registered"):
        register(email="other@test.com", phone="91234567")        # same number, different format
    assert UserAccount.query.count() == 1


def test_designer_application_rejected_when_an_account_has_the_phone(app):
    register(phone="8765 4321")
    with pytest.raises(ValueError, match="Phone number already registered"):
        apply()


def test_designer_application_rejected_when_another_application_is_waiting(app):
    apply()
    with pytest.raises(ValueError, match="Phone number already registered"):
        apply(email="second@studio.com")


def test_customer_cannot_register_with_a_phone_a_pending_application_uses(app):
    apply(phone="9123 4567")
    with pytest.raises(ValueError, match="Phone number already registered"):
        register()


def test_rejected_applicant_can_apply_again_with_the_same_phone(app):
    admin = UserAccount.create("admin@test.com", "password123", "admin", name="Admin")
    application = apply()
    ReviewDesignerApplicationController().reject(application.id, admin.id, "Wrong UEN")
    apply(email="ben2@studio.com")  # no error


def test_approval_fails_if_the_phone_was_taken_in_the_meantime(app):
    admin = UserAccount.create("admin@test.com", "password123", "admin", name="Admin")
    application = apply(phone="9123 4567")
    UserAccount.create("late@test.com", "password123", "customer", name="Late", phone=PHONE)
    with pytest.raises(ValueError, match="Phone number already registered"):
        ReviewDesignerApplicationController().approve(application.id, admin.id)
    assert UserAccount.query.filter_by(role="designer").count() == 0


def test_customer_profile_update_cannot_take_another_accounts_phone(app):
    mine = register()
    UserAccount.create("o@test.com", "password123", "customer", name="Other", phone="+65 81234567")
    with pytest.raises(ValueError, match="Phone number already registered"):
        UpdateProfileController().update(mine.id, "Amy", "Tan", "amy@test.com", "8123 4567", "password123")


def test_keeping_your_own_phone_is_not_a_clash(app):
    mine = register()
    UpdateProfileController().update(mine.id, "Amy", "Tan", "amy@test.com", "9123 4567", "password123")


def test_designer_profile_update_cannot_take_another_accounts_phone(app):
    designer = UserAccount.create("d@test.com", "password123", "designer", name="Dana", phone=PHONE)
    UserAccount.create("o@test.com", "password123", "customer", name="Other", phone="+65 81234567")
    with pytest.raises(ValueError, match="Phone number already registered"):
        UpdateDesignerProfileController().update(designer.id, "Dana", "d@test.com", "8123 4567", "password123")


def test_phone_is_still_encrypted_and_the_lookup_column_does_not_reveal_it(app):
    register()
    raw = db.session.execute(db.text("SELECT phone, phone_hash FROM user_account")).one()
    assert "91234567" not in raw[0] and "91234567" not in (raw[1] or "")
    assert len(raw[1]) == 64


def test_accounts_without_a_phone_do_not_clash(app):
    UserAccount.create("a@test.com", "password123", "admin", name="A")
    UserAccount.create("b@test.com", "password123", "admin", name="B")
