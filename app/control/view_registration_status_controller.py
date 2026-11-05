from app.entity.designer_application import DesignerApplication


# ID-16 View registration status: Pending, Approved or Rejected (with the reason).
class ViewRegistrationStatusController:
    def view(self, application_id):
        application = DesignerApplication.get(application_id) if application_id else None

        if application is None:
            raise LookupError("Application not found.")

        return application
