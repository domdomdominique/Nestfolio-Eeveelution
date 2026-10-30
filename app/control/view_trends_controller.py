from app.entity.idp_view import IDPView
from app.entity.user_account import UserAccount


# ID-20 Trends page: most viewed categories and IDPs across the platform, last 7 or 30 days.
class ViewTrendsController:
    def view(self, account_id, days=7):
        account = UserAccount.get(account_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        if days not in (7, 30):
            raise ValueError("Select the last 7 or 30 days.")

        categories, projects = IDPView.trends(days)

        return {
            "days": days,
            "categories": categories,
            "projects": projects,
        }