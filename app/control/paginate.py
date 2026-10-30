from math import ceil


def paginate(items, page, per_page=25):
    """Return (this page's items, the page number kept in range, number of pages)."""
    pages = max(1, ceil(len(items) / per_page))
    page = min(max(page or 1, 1), pages)
    return items[(page - 1) * per_page:page * per_page], page, pages
