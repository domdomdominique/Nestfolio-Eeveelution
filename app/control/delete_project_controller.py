from app.control.edit_project_controller import EditProjectController


# ID-10 Delete IDP: own IDPs only (the boundary asks to confirm first).
class DeleteProjectController:
    def get_project(self, account_id, idp_id):
        return EditProjectController().get_project(
            account_id,
            idp_id,
        )

    def delete(self, account_id, idp_id):
        project = self.get_project(account_id, idp_id)
        project.delete_project()