from app.entity.idp import IDP


class DeleteIDPController:
    """Control: handles the Interior Designer 'Delete IDP' use case (ID-10)."""

    def delete(self, designer_id, idp_id):
        idp = IDP.get_owned(idp_id, designer_id)
        if idp is None:
            raise LookupError("Project not found.")
        title = idp.title
        idp.delete()
        return title
