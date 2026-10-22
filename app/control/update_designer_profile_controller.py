from app.control.phone_check import ensure_phone_free
from app.control.signup_validation import clean_email, clean_name, clean_phone
from app.entity.designer_application import DesignerApplication
from app.entity.user_account import UserAccount


class UpdateDesignerProfileController:
    """Control: handles the Interior Designer 'Edit ID Profile' use case (ID-18).

    Needs the current password, the same as the customer profile (C-12).
    """

    def update(self, account_id, name, email, phone, current_password):
        account = UserAccount.get(account_id)
        if account is None or account.role != "designer":
            raise LookupError("Account not found.")
        if not account.check_password(current_password):
            raise ValueError("Your current password is incorrect.")
        name = clean_name(name)
        email = clean_email(email)
        phone = clean_phone(phone)
        if email != account.email and (UserAccount.email_exists(email)
                                       or DesignerApplication.has_pending(email)):
            raise ValueError("That email is already used by another account.")
        ensure_phone_free(phone, account_id=account.id)
        account.update_details(name, email, phone)
        return account
