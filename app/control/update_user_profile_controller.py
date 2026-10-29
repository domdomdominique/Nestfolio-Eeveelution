from app.control.profile_validation import clean_profile
from app.entity.user_profile import UserProfile


class UpdateUserProfileController:
    """Control: handles the User Admin 'Update user profile' use case (UA-10).

    Accounts store the profile's key, not its name, so they show the new name.
    """

    def update(self, profile_id, name, description=""):
        profile = UserProfile.get(profile_id)
        if profile is None:
            raise LookupError("User profile not found.")
        name, description = clean_profile(name, description, exclude_id=profile.id)
        profile.update(name, description)
        return profile
