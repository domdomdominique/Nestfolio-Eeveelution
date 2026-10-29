from app.entity.idp_category import IDPCategory


class ViewCategoryController:
    """Control: handles the Platform Management 'View IDP category' use case (PM-04)."""

    def list_categories(self):
        """Every category; each has .name, .description and .idp_count."""
        return IDPCategory.list_all()

    def view(self, category_id):
        category = IDPCategory.get(category_id)
        if category is None:
            raise LookupError("Category not found.")
        return category
