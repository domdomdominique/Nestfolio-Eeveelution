from app.control.account_validation import check_new_password, clean_account
from app.entity.user_account import UserAccount


class CreateUserAccountController:
    """Control: handles the User Admin 'Create user account' use case (UA-03)."""

    def create(self, name, email, phone, password, role):
        name, email, phone, role = clean_account(name, email, phone, role)
        check_new_password(password)
        return UserAccount.create(email, password, role, name=name, phone=phone)  # created Active
