from app.control.signup_validation import (
    clean_email,
    clean_name,
    clean_phone,
)
from app.entity.designer_application import DesignerApplication
from app.entity.user_account import UserAccount


class UpdateDesignerAccountController:
    def update(self, account_id, form):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        name = clean_name(form.get("name"))
        email = clean_email(form.get("email"))
        phone = clean_phone(form.get("phone"))

        if len(name) > 100:
            raise ValueError(
                "Name must be 100 characters or fewer."
            )

        if len(email) > 120:
            raise ValueError(
                "Email must be 120 characters or fewer."
            )

        if email != account.email:
            if (
                UserAccount.email_exists(email)
                or DesignerApplication.has_pending(email)
            ):
                raise ValueError(
                    "That email is already used by another "
                    "account or pending application."
                )

        account.update_details(name, email, phone)

        return account