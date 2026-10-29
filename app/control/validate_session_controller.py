import hashlib

from app.entity.user_account import UserAccount


class ValidateSessionController:
    """Control: is the login in this session still valid? (checked on every request)

    A login only counts while the cookie still matches a real, active account:
    the account exists, is not suspended, has the same role, and has the same
    password as when the user logged in. So a cookie left over from before the
    database was reset, or from before a password change or reset, stops working.
    """

    def token_for(self, account):
        """Fingerprint of the account's current password, stored in the session at log in."""
        return hashlib.sha256(account.password_hash.encode()).hexdigest()[:24]

    def is_valid(self, user_id, role, token):
        if not isinstance(user_id, int) or not role or not token:
            return False
        account = UserAccount.get(user_id)
        return (account is not None and not account.is_blocked and account.role == role
                and token == self.token_for(account))
