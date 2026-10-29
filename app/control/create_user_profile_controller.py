from app.control.profile_validation import clean_profile
from app.entity.user_profile import UserProfile


class CreateUserProfileController:
    """Control: handles the User Admin 'Create user profile with role' use case (UA-08).

    New profiles are Active and can be chosen when creating an account (UA-03).
    """

    def create(self, name, description=""):
        name, description = clean_profile(name, description)
        return UserProfile.create(name, description)
