"""Input checks for the User Admin user profile use cases (UA-08, UA-10)."""
from app.entity.user_profile import UserProfile

MAX_NAME_LENGTH = 50


def clean_profile(name, description, exclude_id=None):
    name = (name or "").strip()
    description = (description or "").strip()
    if not name:
        raise ValueError("Please enter a profile name.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Profile name must be {MAX_NAME_LENGTH} characters or fewer.")
    if UserProfile.name_exists(name, exclude_id):
        raise ValueError(f"A profile called “{name}” already exists.")
    return name, description
