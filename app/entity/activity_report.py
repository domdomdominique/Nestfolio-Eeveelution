import calendar
from datetime import date, datetime, timedelta

from app.entity.db import db


class ActivityReport:
    """Entity: platform activity between two dates (PM-08 daily, PM-09 weekly, PM-10 monthly).

    Not stored in the database: the figures are counted from the records
    each time, so they always match the system (acceptance criterion 4).
    `start` is inclusive and `end` exclusive.
    """

    TOP_N = 5

    def __init__(self, kind, start, end):
        self.kind, self.start, self.end = kind, start, end
        self.generated_at = datetime.now()
        self._count_figures()

    # --- Building a report for a period -------------------------------------

    @classmethod
    def daily(cls, day):
        return cls("daily", day, day + timedelta(days=1))

    @classmethod
    def weekly(cls, any_day):
        """PM-09 The Monday-to-Sunday week containing any_day."""
        monday = any_day - timedelta(days=any_day.weekday())
        return cls("weekly", monday, monday + timedelta(days=7))

    @classmethod
    def monthly(cls, year, month):
        first = date(year, month, 1)
        return cls("monthly", first, first + timedelta(days=calendar.monthrange(year, month)[1]))

    @property
    def title(self):
        if self.kind == "daily":
            return f"Daily report: {self.start:%d %b %Y}"
        if self.kind == "weekly":
            return f"Weekly report: {self.start:%d %b} to {self.end - timedelta(days=1):%d %b %Y}"
        return f"Monthly report: {self.start:%B %Y}"

    @property
    def file_stem(self):
        """e.g. daily_report_2026-10-13, weekly_report_2026-10-12, monthly_report_2026-10 (PM-11)."""
        stamp = f"{self.start:%Y-%m}" if self.kind == "monthly" else self.start.isoformat()
        return f"{self.kind}_report_{stamp}"

    # --- Counting -------------------------------------------------------------

    def _between(self, column):
        start = datetime.combine(self.start, datetime.min.time())
        end = datetime.combine(self.end, datetime.min.time())
        return db.and_(column >= start, column < end)

    def _count_figures(self):
        from app.entity.favourite import Favourite
        from app.entity.idp import IDP
        from app.entity.idp_view import IDPView
        from app.entity.user_account import UserAccount

        self.new_accounts = UserAccount.query.filter(self._between(UserAccount.created_at)).count()
        self.new_idps = IDP.query.filter(self._between(IDP.created_at)).count()
        self.total_views = IDPView.query.filter(self._between(IDPView.viewed_at)).count()
        self.total_shortlists = Favourite.query.filter(self._between(Favourite.saved_at)).count()

        views = (IDPView, IDPView.idp_id, IDPView.viewed_at)
        saves = (Favourite, Favourite.idp_id, Favourite.saved_at)
        self.most_viewed_idps = self._top_idps(*views)
        self.most_shortlisted_idps = self._top_idps(*saves)
        self.most_viewed_categories = self._top_categories(*views)
        self.most_shortlisted_categories = self._top_categories(*saves)

    def _top_idps(self, model, idp_column, time_column):
        from app.entity.idp import IDP

        total = db.func.count(model.id)
        rows = (db.session.query(IDP.title, IDP.category, total)
                .join(model, idp_column == IDP.id)
                .filter(self._between(time_column))
                .group_by(IDP.id).order_by(total.desc(), IDP.title)
                .limit(self.TOP_N))
        return [(title, category, count) for title, category, count in rows]

    def _top_categories(self, model, idp_column, time_column):
        from app.entity.idp import IDP

        total = db.func.count(model.id)
        rows = (db.session.query(IDP.category, total)
                .join(model, idp_column == IDP.id)
                .filter(self._between(time_column))
                .group_by(IDP.category).order_by(total.desc(), IDP.category)
                .limit(self.TOP_N))
        return [(category, count) for category, count in rows]

    # --- For downloads (PM-11) -------------------------------------------------

    def summary_rows(self):
        return [
            ("New user accounts", self.new_accounts),
            ("New IDPs", self.new_idps),
            ("Total IDP views", self.total_views),
            ("Total shortlists", self.total_shortlists),
        ]

    def sections(self):
        """(heading, column headings, rows) for each ranked list."""
        return [
            ("Most viewed IDPs", ("IDP", "Category", "Views"), self.most_viewed_idps),
            ("Most shortlisted IDPs", ("IDP", "Category", "Shortlists"), self.most_shortlisted_idps),
            ("Most viewed categories", ("Category", "Views"), self.most_viewed_categories),
            ("Most shortlisted categories", ("Category", "Shortlists"), self.most_shortlisted_categories),
        ]
