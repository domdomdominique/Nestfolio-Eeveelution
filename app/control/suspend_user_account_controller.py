from app.entity.user_account import UserAccount


class SuspendUserAccountController:
    """Control: handles the User Admin 'Suspend user account' use case (UA-06).

    The boundary asks for confirmation first. The account and its data are
    kept; it just cannot log in.
    """

    def suspend(self, admin_id, account_id):
        account = UserAccount.get(account_id)
        if account is None:
            raise LookupError("User account not found.")
        if account.id == admin_id:
            raise ValueError("You cannot suspend your own account.")
        if account.is_suspended:
            raise ValueError("This account is already suspended.")
        account.set_suspended(True)
        return account
