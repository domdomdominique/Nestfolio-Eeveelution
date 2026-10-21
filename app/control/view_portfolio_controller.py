from app.entity.idp import IDP
from app.entity.user_account import UserAccount


class ViewPortfolioController:
    def view(self, account_id):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        return IDP.by_designer(account.id)