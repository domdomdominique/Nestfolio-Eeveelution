from app.control.account_validation import check_new_password, clean_account
from app.entity.user_account import UserAccount


class CreateUserAccountController:
    """Control: handles the User Admin 'Create user account' use case (UA-03)."""

    def create(self, name, email, phone, password, role):
        # Checks the name, that the email and phone are not already used, and that the profile is active.
        name, email, phone, role = clean_account(name, email, phone, role)
        check_new_password(password)
        # Active, but the user must pick their own password at first login
        return UserAccount.create(email, password, role, name=name, phone=phone,
                                  must_change_password=True)
