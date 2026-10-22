from app.control.phone_check import ensure_phone_free
from app.control.signup_validation import clean_email, clean_phone
from app.entity.designer_application import DesignerApplication
from app.entity.user_account import UserAccount


class UpdateProfileController:
    """Control: handles the Customer 'Update Customer Profile' use case (C-12).

    The current password must be given, so someone at an unlocked screen cannot
    change the details (and the email used to log in).
    """

    def update(self, account_id, first_name, last_name, email, phone, current_password):
        account = UserAccount.get(account_id)
        if account is None:
            raise LookupError("Account not found.")
        if not account.check_password(current_password):
            raise ValueError("Your current password is incorrect.")
        first_name, last_name = (first_name or "").strip(), (last_name or "").strip()
        if not first_name:
            raise ValueError("Please enter your first name.")
        email = clean_email(email)
        phone = clean_phone(phone)
        if email != account.email and (UserAccount.email_exists(email)
                                       or DesignerApplication.has_pending(email)):
            raise ValueError("That email is already used by another account.")
        ensure_phone_free(phone, account_id=account.id)
        account.update_details(f"{first_name} {last_name}".strip(), email, phone)
        return account
