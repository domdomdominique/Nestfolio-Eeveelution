from app.entity.user_account import UserAccount


class ReactivateUserAccountController:
    """Control: handles the User Admin 'Reactivate suspended user account' use case (UA-13).

    The boundary only shows Reactivate for suspended accounts and asks for
    confirmation first.
    """

    def reactivate(self, account_id):
        account = UserAccount.get(account_id)
        if account is None:
            raise LookupError("User account not found.")
        if not account.is_suspended:
            raise ValueError("Only suspended accounts can be reactivated.")
        account.set_suspended(False)
        return account
