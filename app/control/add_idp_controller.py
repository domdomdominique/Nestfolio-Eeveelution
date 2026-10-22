from app.control.idp_validation import clean_idp_fields
from app.entity.idp import IDP


class AddIDPController:
    """Control: handles the Interior Designer 'Add IDP to Portfolio' use case (ID-06)."""

    def add(self, designer_id, title, description, category, status):
        title, description, category, is_current = clean_idp_fields(title, description, category, status)
        return IDP.create(designer_id, title, description, category, is_current)

    def categories(self):
        return IDP.categories()
