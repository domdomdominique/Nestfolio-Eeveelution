from math import ceil

from app.entity.idp import IDP
from app.entity.user_account import UserAccount


PER_PAGE = 8


# ID-07 View portfolio list and ID-08 search it: only the designer's own IDPs.
class ViewPortfolioController:
    def _check_designer(self, designer_id):
        account = UserAccount.get(designer_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

        return account

    def view(
        self,
        designer_id,
        keyword="",
        status=None,
        category=None,
        page=1,
    ):
        self._check_designer(designer_id)

        keyword = (keyword or "").strip()[:100]
        status = status if status in ("current", "past") else None

        categories = IDP.categories()
        category = category if category in categories else None

        total = IDP.portfolio_count(
            designer_id,
            keyword,
            status,
            category,
        )

        pages = max(1, ceil(total / PER_PAGE))
        page = min(max(page or 1, 1), pages)

        return {
            "projects": IDP.portfolio(
                designer_id,
                keyword,
                status,
                category,
                limit=PER_PAGE,
                offset=(page - 1) * PER_PAGE,
            ),
            "counts": IDP.status_counts_for_designer(designer_id),
            "total": total,
            "page": page,
            "pages": pages,
            "per_page": PER_PAGE,
            "keyword": keyword,
            "status": status,
            "category": category,
            "categories": categories,
        }

    def all_projects(self, designer_id):
        """Return every owned project for the statistics page."""
        account = self._check_designer(designer_id)
        return IDP.by_designer(account.id)