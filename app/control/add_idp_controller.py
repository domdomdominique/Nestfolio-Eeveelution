from app.control.idp_validation import clean_idp_fields
from app.control.portfolio_validation import validated_photos
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


# ID-06 Add IDP to portfolio, with ID-12 category and ID-19 photos.
class AddIDPController:
    @property
    def CATEGORIES(self):
        """Current categories from Platform Management (PM-03 to PM-06)."""
        return IDP.categories()

    def categories(self):
        return IDP.categories()

    def add(self, account_id, form, files=()):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        title, description, category, is_current = clean_idp_fields(
            form.get("title"),
            form.get("description"),
            form.get("category"),
            form.get("status"),
        )
        photos = validated_photos(files)

        return IDP.create_for_designer(
            account.id,
            title,
            description,
            category,
            is_current,
            photos=photos,
        )
