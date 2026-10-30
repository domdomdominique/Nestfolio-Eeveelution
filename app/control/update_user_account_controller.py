from app.control.account_validation import clean_account
from app.entity.user_account import UserAccount


class UpdateUserAccountController:
    """Control: handles the User Admin 'Update user account' use case (UA-05)."""

    def update(self, account_id, name, email, phone, role, admin_id=None):
        account = UserAccount.get(account_id)
        if account is None:
            raise LookupError("User account not found.")
        name, email, phone, role = clean_account(name, email, phone, role, account_id=account.id)
        if account.id == admin_id and role != account.role:
            raise ValueError("You cannot change your own user profile.")
        account.update_by_admin(name, email, phone, role)
        return account
