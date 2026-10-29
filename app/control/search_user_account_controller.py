from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile


class SearchUserAccountController:
    """Control: handles the User Admin 'Search user account' use case (UA-07).

    Searches name or email; can filter by user profile (role key) and status
    ('active' / 'suspended'). An empty list means "No results found".
    """

    STATUSES = {"active": "Active", "suspended": "Suspended"}

    def search(self, keyword="", role=None, status=None):
        return UserAccount.search(
            keyword=(keyword or "").strip(),
            role=role if role and UserProfile.by_key(role) else None,
            status=status if status in self.STATUSES else None,
        )

    def profile_choices(self):
        return [(p.key, p.name) for p in UserProfile.list_all()]
