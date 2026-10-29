from app.entity.user_account import UserAccount


class ViewUserAccountController:
    """Control: handles the User Admin 'View user account' use case (UA-04).

    Returns only the details the page may show: never the password or its hash.
    """

    def view(self, account_id):
        account = UserAccount.get(account_id)
        if account is None:
            raise LookupError("User account not found.")
        return {
            "id": account.id,
            "name": account.name,
            "email": account.email,
            "phone": account.phone,
            "profile": account.profile_name,
            "role": account.role,
            "status": account.status,
            "created_at": account.created_at,
            "must_change_password": bool(account.must_change_password),
        }
