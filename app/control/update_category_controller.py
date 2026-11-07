from app.control.category_validation import clean_category, clean_category_photo
from app.entity.idp_category import IDPCategory


class UpdateCategoryController:
    """Control: handles the Platform Management 'Update IDP category' use case (PM-05)."""

    def update(self, category_id, name, description="", photo=None):
        category = IDPCategory.get(category_id)
        if category is None:
            raise LookupError("Category not found.")
        name, description = clean_category(name, description, exclude_id=category.id)
        # A new background is optional when editing; leaving it empty keeps the current one
        photo = clean_category_photo(photo)
        category.update(name, description, photo)  # also renames it on every IDP using it
        return category
