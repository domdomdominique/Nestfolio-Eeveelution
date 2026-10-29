"""Input checks for the User Admin account use cases (UA-03, UA-05)."""
from app.control.phone_check import ensure_phone_free
from app.control.signup_validation import (MIN_PASSWORD_LENGTH, clean_email, clean_name,
                                           clean_phone)
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile


def clean_account(name, email, phone, role, account_id=None):
    """Return cleaned (name, email, phone, role) or raise ValueError."""
    name, email, phone = clean_name(name), clean_email(email), clean_phone(phone)
    if UserAccount.email_taken_by_other(email, account_id):
        raise ValueError("Email already registered to another account.")
    ensure_phone_free(phone, account_id)  # same check as sign-up (unique phone)
    profile = UserProfile.by_key(role or "")
    if profile is None:
        raise ValueError("Please choose a user profile.")
    current = UserAccount.get(account_id) if account_id else None
    # Only active profiles can be chosen (UA-03 / UA-11), but an account
    # already on a suspended profile can be edited without changing it.
    if not profile.is_active and not (current and current.role == profile.key):
        raise ValueError(f"The “{profile.name}” profile is suspended and cannot be assigned.")
    return name, email, phone, profile.key


def check_new_password(password):
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
