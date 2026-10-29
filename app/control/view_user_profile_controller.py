from app.entity.user_profile import UserProfile


class ViewUserProfileController:
    """Control: handles the User Admin 'View user profile' use case (UA-09).

    Each profile has .name, .description, .status and .account_count.
    """

    def list_profiles(self):
        return UserProfile.list_all()

    def view(self, profile_id):
        profile = UserProfile.get(profile_id)
        if profile is None:
            raise LookupError("User profile not found.")
        return profile
