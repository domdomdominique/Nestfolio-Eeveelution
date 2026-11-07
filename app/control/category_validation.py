"""Shared input checks for the IDP category use cases (PM-03, PM-05)."""
from app.control.portfolio_validation import IDP_MAX_PHOTO_BYTES, validated_photos
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


def clean_category_photo(upload, required=False):
    """The category background as {filename, content_type, data}, or None when none was chosen.
    Raises ValueError when it is required but missing, or is not a valid JPG/PNG up to 10 MB."""
    photos = validated_photos([upload] if upload and upload.filename else [],
                              max_bytes=IDP_MAX_PHOTO_BYTES)
    if not photos:
        if required:
            raise ValueError("Please upload a background image for the category.")
        return None
    return photos[0]
