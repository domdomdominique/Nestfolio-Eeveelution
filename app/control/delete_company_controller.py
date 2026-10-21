from app.entity.designer_company import DesignerCompany
from app.entity.user_account import UserAccount


class DeleteCompanyController:
    def delete(self, account_id):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        if not account.company:
            raise ValueError(
                "There is no company information to delete."
            )

        DesignerCompany.delete_for(account.id)