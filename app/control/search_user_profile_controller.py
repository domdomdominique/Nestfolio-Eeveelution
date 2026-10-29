from app.entity.user_profile import UserProfile


class SearchUserProfileController:
    """Control: handles the User Admin 'Search user profile' use case (UA-12).

    An empty list means the boundary shows "No results found".
    """

    def search(self, keyword):
        return UserProfile.list_all((keyword or "").strip())
