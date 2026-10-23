"""Shared checks for the designer's add and edit IDP forms (ID-06, ID-09, ID-11, ID-12)."""
from app.entity.idp import IDP

TITLE_MAX = 150
DESCRIPTION_MAX = 1000
STATUSES = ("current", "past")


def clean_idp_fields(title, description, category, status):
    """Return (title, description, category, is_current) or raise ValueError with a form message."""
    title = (title or "").strip()
    description = (description or "").strip()
    if not title:
        raise ValueError("Please enter a project title.")
    if len(title) > TITLE_MAX:
        raise ValueError(f"The title must be {TITLE_MAX} characters or fewer.")
    if len(description) > DESCRIPTION_MAX:
        raise ValueError(f"The description must be {DESCRIPTION_MAX} characters or fewer.")
    if category not in IDP.categories():
        raise ValueError("Please choose a category from the list.")
    return title, description, category, clean_status(status) == "current"


def clean_status(status):
    if status not in STATUSES:
        raise ValueError("Please choose Current or Past.")
    return status
