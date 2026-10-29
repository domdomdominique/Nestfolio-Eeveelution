from app.entity.idp_category import IDPCategory


class DeleteCategoryController:
    """Control: handles the Platform Management 'Delete IDP category' use case (PM-06).

    The boundary asks for confirmation first; this only runs once confirmed.
    """

    def delete(self, category_id):
        category = IDPCategory.get(category_id)
        if category is None:
            raise LookupError("Category not found.")
        in_use = category.idp_count
        if in_use:
            raise ValueError(f"“{category.name}” cannot be deleted because "
                             f"{in_use} IDP{'s' if in_use != 1 else ''} still use{'' if in_use != 1 else 's'} it.")
        name = category.name
        category.delete()
        return name
