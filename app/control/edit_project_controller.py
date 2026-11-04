from app.control.idp_validation import clean_idp_fields
from app.control.portfolio_validation import validated_photos
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


# ID-09 Edit IDP: own IDPs only; also adds photos (ID-19).
class EditProjectController:
    @property
    def CATEGORIES(self):
        """Current categories from Platform Management (PM-03 to PM-06)."""
        return IDP.categories()

    def get_project(self, account_id, idp_id):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        project = IDP.get(idp_id)

        if project is None or project.designer_id != account.id:
            raise LookupError("Project not found.")

        return project

    def update(self, account_id, idp_id, form, files=()):
        project = self.get_project(account_id, idp_id)

        title, description, category, is_current = clean_idp_fields(
            form.get("title"),
            form.get("description"),
            form.get("category"),
            form.get("status"),
        )

        photos = validated_photos(
            files,
            len(project.photos),
        )

        project.update_details(
            title,
            description,
            category,
            is_current,
            photos=photos,
        )

        return project
