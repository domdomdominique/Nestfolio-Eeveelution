from app.entity.user_account import UserAccount


class ViewDesignerAccountController:
    def view(self, account_id):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        return account

    def registration_status(self, account_id):
        account = self.view(account_id)

        application = getattr(
            account,
            "designer_application",
            None,
        )

        if application:
            return application.status.title()

        return "Active (no registration application)"