from app.control.category_validation import clean_category, clean_category_photo
from app.entity.idp_category import IDPCategory


class CreateCategoryController:
    """Control: handles the Platform Management 'Create IDP category' use case (PM-03).

    A new category must come with a background image (shown on its landing-page card).
    """

    def create(self, name, description="", photo=None):
        name, description = clean_category(name, description)
        photo = clean_category_photo(photo, required=True)
        return IDPCategory.create(name, description, photo)
