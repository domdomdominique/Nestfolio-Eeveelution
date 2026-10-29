from app.control.category_validation import clean_category
from app.entity.idp_category import IDPCategory


class CreateCategoryController:
    """Control: handles the Platform Management 'Create IDP category' use case (PM-03)."""

    def create(self, name, description=""):
        name, description = clean_category(name, description)
        return IDPCategory.create(name, description)
