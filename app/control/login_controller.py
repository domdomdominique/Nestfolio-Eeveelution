from werkzeug.security import check_password_hash

from app.entity.designer_application import DesignerApplication
from app.entity.user_account import UserAccount


class LoginController:
    """Handles login for customers, designers, admins and platform managers."""

    def login(self, email, password, role=None):
        email = (email or "").strip().lower()

        account = UserAccount.login(email, password)

        # The account must match the role selected on the login form.
        if account and role and account.role != role:
            return None

        return account

    def application_status(self, email):
        email = (email or "").strip().lower()

        if UserAccount.email_exists(email):
            return None

        application = DesignerApplication.latest_for(email)

        return application.status if application else None

    def failure_message(self, email, password, role=None):
        email = (email or "").strip().lower()

        account = UserAccount.find_by_email(email)

        if account:
            correct_password = account.check_password(password)
            correct_role = not role or account.role == role

            if correct_password and correct_role and account.is_blocked:
                return (
                    "Your account is suspended. "
                    "Please contact the administrator."
                )

            return "Invalid email or password."

        # Pending/rejected applicants do not have a login account yet.
        application = DesignerApplication.latest_for(email)

        if application and role in (None, "designer"):
            correct_password = check_password_hash(
                application.password_hash,
                password or "",
            )

            if correct_password:
                if application.status == "pending":
                    return (
                        "Your designer application is still being reviewed. "
                        "You can log in once it is approved."
                    )

                if application.status == "rejected":
                    return (
                        "Your designer application was not approved. "
                        "Please contact the administrator for details."
                    )

        return "Invalid email or password."