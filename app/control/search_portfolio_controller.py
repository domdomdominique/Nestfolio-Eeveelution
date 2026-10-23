from app.entity.idp import IDP
from app.entity.user_account import UserAccount


class SearchPortfolioController:
    def search(self, account_id, keyword):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        return IDP.search_for_designer(
            account.id,
            keyword,
        )