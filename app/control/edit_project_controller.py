from app.control.portfolio_validation import (
    project_details,
    validated_photos,
)
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


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

        details = project_details(form)

        photos = validated_photos(
            files,
            len(project.photos),
        )

        project.update_details(
            **details,
            photos=photos,
        )

        return project