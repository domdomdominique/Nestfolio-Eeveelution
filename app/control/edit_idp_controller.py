from app.control.idp_validation import clean_idp_fields
from app.entity.idp import IDP


class EditIDPController:
    """Control: handles the Interior Designer 'Edit IDP' use case (ID-09)."""

    def get(self, designer_id, idp_id):
        """The designer's own IDP for the pre-filled form; LookupError if it is not theirs."""
        idp = IDP.get_owned(idp_id, designer_id)
        if idp is None:
            raise LookupError("Project not found.")
        return idp

    def edit(self, designer_id, idp_id, title, description, category, status):
        idp = self.get(designer_id, idp_id)
        idp.update(*clean_idp_fields(title, description, category, status))
        return idp

    def categories(self):
        return IDP.categories()
