import secrets
import string

from app.entity.user_account import UserAccount


class ResetPasswordController:
    """Control: handles the User Admin 'Reset user password' use case (UA-16).

    Makes a random temporary password, returns it once for the page to show,
    and makes the user change it at their next login. The existing password
    is only ever stored as a hash, so the admin can never see it.
    """

    LENGTH = 12
    ALPHABET = string.ascii_letters + string.digits

    def reset(self, account_id):
        account = UserAccount.get(account_id)
        if account is None:
            raise LookupError("User account not found.")
        temporary = "".join(secrets.choice(self.ALPHABET) for _ in range(self.LENGTH))
        account.reset_password(temporary)
        return temporary

    def must_change_password(self, account_id):
        """For the login boundary: send the user to Change password (C-14) if True."""
        account = UserAccount.get(account_id)
        return bool(account and account.must_change_password)
