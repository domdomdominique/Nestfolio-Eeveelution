from app.entity.user_account import UserAccount


# ID-04 View company information: a designer sees only their own.
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