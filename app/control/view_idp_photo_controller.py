from app.entity.idp_photo import IDPPhoto


class ViewIDPPhotoController:
    def view(self, photo_id):
        photo = IDPPhoto.get(photo_id)

        if (
            photo is None
            or photo.idp is None
            or not photo.idp.is_visible
        ):
            raise LookupError("Photo not found.")

        return photo