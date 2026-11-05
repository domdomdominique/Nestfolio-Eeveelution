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

    def projects(self, category, keyword=""):
        """PM-04 The IDPs in this category, newest first, optionally filtered by title or designer."""
        projects = category.projects
        keyword = (keyword or "").strip().lower()
        if keyword:
            projects = [p for p in projects
                        if keyword in p.title.lower()
                        or (p.designer and keyword in p.designer.display_name.lower())]
        return projects
