"""Shared 'is this phone number free?' check for every use case that saves a phone."""
from app.entity.designer_application import DesignerApplication
from app.entity.user_account import UserAccount

PHONE_TAKEN = "Phone number already registered."


def ensure_phone_free(phone, account_id=None, ignore_pending=False):
    """Raise ValueError if another account, or a waiting designer application, has this phone.

    account_id is the account being edited, so keeping your own number is allowed.
    """
    if UserAccount.phone_exists(phone, exclude_id=account_id):
        raise ValueError(PHONE_TAKEN)
    if not ignore_pending and DesignerApplication.phone_pending(phone):
        raise ValueError(PHONE_TAKEN)
