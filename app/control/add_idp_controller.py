from collections.abc import Mapping

from app.control.idp_validation import clean_idp_fields
from app.control.portfolio_validation import validated_photos
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


class AddIDPController:
    @property
    def CATEGORIES(self):
        """Current categories from Platform Management (PM-03 to PM-06)."""
        return IDP.categories()

    def categories(self):
        return IDP.categories()

    def add(
        self,
        account_id,
        title,
        description=None,
        category=None,
        status=None,
        *,
        files=(),
    ):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        if isinstance(title, Mapping):
            # Your route supplies a form and optional uploaded files.
            form = title

            if description is not None:
                files = description

            values = clean_idp_fields(
                form.get("title"),
                form.get("description"),
                form.get("category"),
                form.get("status"),
            )
        else:
            # Existing team code supplies individual field values.
            values = clean_idp_fields(
                title,
                description,
                category,
                status,
            )

        clean_title, clean_description, clean_category, is_current = values
        photos = validated_photos(files)

        return IDP.create_for_designer(
            account.id,
            clean_title,
            clean_description,
            clean_category,
            is_current,
            photos=photos,
        )