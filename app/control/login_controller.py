from werkzeug.security import check_password_hash

from app.entity.designer_application import DesignerApplication
from app.entity.user_account import UserAccount


# C-02, ID-01, PM-01, UA-01 Log in for every role: same error for a wrong email or password, suspended accounts refused.
class LoginController:
    """Handles login for customers, designers, admins and platform managers."""

    def login(self, email, password):
        email = (email or "").strip().lower()

        return UserAccount.login(email, password)

    def unapproved_application(self, email, password):
        """A designer applicant with no account yet (pending or rejected) who gave the right password."""
        email = (email or "").strip().lower()

        if UserAccount.email_exists(email):
            return None

        application = DesignerApplication.latest_for(email)

        if application and check_password_hash(application.password_hash, password or ""):
            return application

        return None

    def failure_message(self, email, password):
        email = (email or "").strip().lower()

        account = UserAccount.find_by_email(email)

        if account:
            if account.check_password(password) and account.is_blocked:
                return (
                    "Your account is suspended. "
                    "Please contact the administrator."
                )

            return "Invalid email or password."

        return "Invalid email or password."
