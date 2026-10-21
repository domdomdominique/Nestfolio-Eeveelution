from app.control.portfolio_validation import (
    project_details,
    validated_photos,
)
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


class AddIDPController:
    CATEGORIES = IDP.CATEGORIES

    def add(self, account_id, form, files=()):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        details = project_details(form)
        photos = validated_photos(files)

        return IDP.create_for_designer(
            account.id,
            **details,
            photos=photos,
        )