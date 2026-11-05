from datetime import date, datetime, timedelta
from functools import cached_property

from app.entity.db import db


class ActivityTimeline:
    """Entity: IDP views and shortlists counted per hour or per day, for the
    over-time charts on the Reports (PM-08 to PM-10), Statistics (ID-13, ID-14)
    and Trends (ID-20) pages. count() does the same for any other dated record,
    e.g. new accounts or reported projects on the User Admin dashboard.

    Not stored in the database: like ActivityReport, it is counted from the
    IDPView and Favourite records every time, so the chart always matches them.
    Every hour or day in the period is included, with 0 when nothing happened,
    and None for hours or days that have not happened yet (so charts stop at now).
    """

    def __init__(self, start, end, unit="day", designer_id=None, visible_only=False):
        self.start, self.end, self.unit = start, end, unit      # start inclusive, end exclusive
        self.designer_id, self.visible_only = designer_id, visible_only
        self.keys = self._keys()
        self.labels = [self._label(k) for k in self.keys]

    @classmethod
    def last_days(cls, days, **filters):
        """The last `days` days up to and including today."""
        today = date.today()
        return cls(today - timedelta(days=days - 1), today + timedelta(days=1), "day", **filters)

    @property
    def total_views(self):
        return sum(v for v in self.views if v is not None)

    @property
    def total_shortlists(self):
        return sum(v for v in self.shortlists if v is not None)

    # --- Buckets ------------------------------------------------------------------

    def _keys(self):
        start = datetime.combine(self.start, datetime.min.time())
        end = datetime.combine(self.end, datetime.min.time())
        step = timedelta(hours=1) if self.unit == "hour" else timedelta(days=1)
        keys, moment = [], start
        while moment < end:
            keys.append(moment.strftime(self._format_python()))
            moment += step
        return keys

    def _format_python(self):
        return "%Y-%m-%d %H" if self.unit == "hour" else "%Y-%m-%d"

    def _label(self, key):
        if self.unit == "hour":
            return f"{int(key[-2:]):02d}:00"
        return datetime.strptime(key, "%Y-%m-%d").strftime("%d %b")

    def _bucket(self, column):
        return db.func.strftime("%Y-%m-%d %H" if self.unit == "hour" else "%Y-%m-%d", column)

    def _between(self, column):
        start = datetime.combine(self.start, datetime.min.time())
        end = datetime.combine(self.end, datetime.min.time())
        return db.and_(column >= start, column < end)

    def _fill(self, rows):
        counts = dict(rows)
        now = datetime.now().strftime(self._format_python())
        return [None if k > now else counts.get(k, 0) for k in self.keys]

    # --- Counting -----------------------------------------------------------------

    @cached_property
    def views(self):
        return self._count_views()

    @cached_property
    def shortlists(self):
        return self._count_shortlists()

    def count(self, column, *conditions):
        """Records per hour or day by a DateTime column, e.g. count(UserAccount.created_at)."""
        bucket = self._bucket(column)
        query = (db.session.query(bucket, db.func.count())
                 .filter(self._between(column), *conditions).group_by(bucket))
        return self._fill(query.all())

    def _restrict(self, query, idp_column):
        from app.entity.idp import IDP

        if self.designer_id is None and not self.visible_only:
            return query
        query = query.join(IDP, idp_column == IDP.id)
        if self.designer_id is not None:
            query = query.filter(IDP.designer_id == self.designer_id)
        if self.visible_only:
            query = IDP.visible(query)
        return query

    def _count_views(self):
        from app.entity.idp_view import IDPView

        bucket = self._bucket(IDPView.viewed_at)
        query = db.session.query(bucket, db.func.count(IDPView.id)).filter(self._between(IDPView.viewed_at))
        return self._fill(self._restrict(query, IDPView.idp_id).group_by(bucket).all())

    def _count_shortlists(self):
        from app.entity.favourite import Favourite

        bucket = self._bucket(Favourite.saved_at)
        query = db.session.query(bucket, db.func.count(Favourite.id)).filter(self._between(Favourite.saved_at))
        return self._fill(self._restrict(query, Favourite.idp_id).group_by(bucket).all())
