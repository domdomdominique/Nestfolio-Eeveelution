from app.control.edit_project_controller import EditProjectController
from app.entity.idp_photo import IDPPhoto


class RemoveProjectPhotoController:
    def remove(self, account_id, idp_id, photo_id):
        project = EditProjectController().get_project(
            account_id,
            idp_id,
        )

        photo = IDPPhoto.get(photo_id)

        if photo is None or photo.idp_id != project.id:
            raise LookupError("Photo not found.")

        photo.delete()