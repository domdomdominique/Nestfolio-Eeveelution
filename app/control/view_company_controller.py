from app.entity.user_account import UserAccount


class ViewCompanyController:
    def view(self, account_id):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        return account.company