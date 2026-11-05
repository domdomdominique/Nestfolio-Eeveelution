from app.entity.idp_category import IDPCategoryPhoto


class ViewCategoryPhotoController:
    """Control: the background photo of a category card on the landing page."""

    def view(self, category_id):
        photo = IDPCategoryPhoto.get(category_id)
        if photo is None:
            raise LookupError("Photo not found.")
        return photo
