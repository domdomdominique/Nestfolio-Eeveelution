from math import ceil

from app.entity.idp import IDP

PER_PAGE = 8


class ViewPortfolioController:
    """Control: handles 'View Portfolio List' and 'Search IDPs' for a designer (ID-07, ID-08).

    The view and shortlist counts shown on each row are ID-13 and ID-14.
    """

    def view(self, designer_id, keyword="", status=None, category=None, page=1):
        keyword = (keyword or "").strip()[:100]
        status = status if status in ("current", "past") else None
        category = category if category in IDP.categories() else None
        total = IDP.portfolio_count(designer_id, keyword, status, category)
        pages = max(1, ceil(total / PER_PAGE))
        page = min(max(page or 1, 1), pages)
        return {
            "projects": IDP.portfolio(designer_id, keyword, status, category,
                                      limit=PER_PAGE, offset=(page - 1) * PER_PAGE),
            "counts": IDP.status_counts_for_designer(designer_id),
            "total": total, "page": page, "pages": pages, "per_page": PER_PAGE,
            "keyword": keyword, "status": status, "category": category,
            "categories": IDP.categories(),
        }
