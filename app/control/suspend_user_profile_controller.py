from app.entity.user_profile import UserProfile


class SuspendUserProfileController:
    """Control: handles the User Admin 'Suspend user profile' use case (UA-11).

    The boundary asks for confirmation first. Accounts on a suspended profile
    cannot log in, and it cannot be given to new accounts. The User Admin
    profile can never be suspended.
    """

    def suspend(self, profile_id):
        profile = UserProfile.get(profile_id)
        if profile is None:
            raise LookupError("User profile not found.")
        profile.suspend()
        return profile
