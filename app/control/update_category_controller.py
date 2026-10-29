from app.control.category_validation import clean_category
from app.entity.idp_category import IDPCategory


class UpdateCategoryController:
    """Control: handles the Platform Management 'Update IDP category' use case (PM-05)."""

    def update(self, category_id, name, description=""):
        category = IDPCategory.get(category_id)
        if category is None:
            raise LookupError("Category not found.")
        name, description = clean_category(name, description, exclude_id=category.id)
        category.update(name, description)  # also renames it on every IDP using it
        return category
