from app.entity.idp_category import IDPCategory


class SearchCategoryController:
    """Control: handles the Platform Management 'Search IDP category' use case (PM-07).

    An empty result means the boundary shows "No results found".
    """

    def search(self, keyword):
        return IDPCategory.list_all((keyword or "").strip())
