from app.control.edit_project_controller import EditProjectController


class DeleteProjectController:
    def get_project(self, account_id, idp_id):
        return EditProjectController().get_project(
            account_id,
            idp_id,
        )

    def delete(self, account_id, idp_id):
        project = self.get_project(account_id, idp_id)
        project.delete_project()