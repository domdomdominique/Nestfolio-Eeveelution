from werkzeug.security import check_password_hash

from app.entity.designer_application import DesignerApplication


# ID-16 View registration status: Pending, Approved or Rejected (with the reason).
class ViewRegistrationStatusController:
    def authenticate(self, email, password):
        email = (email or "").strip().lower()

        application = DesignerApplication.latest_for(email)

        if not application or not check_password_hash(
            application.password_hash,
            password or "",
        ):
            raise ValueError("Invalid email or password.")

        return application

    def view(self, application_id):
        application = DesignerApplication.get(application_id)

        if application is None:
            raise LookupError("Application not found.")

        return application