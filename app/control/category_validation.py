"""Shared input checks for the IDP category use cases (PM-03, PM-05)."""
from app.entity.idp_category import IDPCategory

MAX_NAME_LENGTH = 50


def clean_category(name, description, exclude_id=None):
    """Return (name, description) or raise ValueError with a message for the page."""
    name = (name or "").strip()
    description = (description or "").strip()
    if not name:
        raise ValueError("Please enter a category name.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Category name must be {MAX_NAME_LENGTH} characters or fewer.")
    if IDPCategory.name_exists(name, exclude_id):
        raise ValueError(f"A category called “{name}” already exists.")
    return name, description
