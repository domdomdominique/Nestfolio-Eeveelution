from datetime import timedelta

from app.entity.activity_timeline import ActivityTimeline
from app.entity.designer_application import DesignerApplication
from app.entity.report import Report
from app.entity.user_account import UserAccount


def change(value, previous):
    """Whole-percentage change, "new" when the previous period had none, or None when both are 0."""
    if previous:
        return round((value - previous) * 100 / previous)
    return "new" if value else None


def change_text(value):
    """e.g. +25%, -10%, 0%, new, or a dash when there was nothing in either period."""
    if value is None:
        return "-"
    if value == "new":
        return "new"
    return f"{value:+d}%" if value else "0%"


class ViewAdminActivityController:
    """Control: the User Admin dashboard's over-time charts:
    new user accounts, designer applications received, projects reported and reports
    resolved, per day, compared with the same number of days before.

    Counted from the records every time (like the Platform Management reports), so the
    charts always match the Accounts, Applications and Reported projects pages.
    """

    PERIODS = (7, 30, 90)
    DEFAULT_DAYS = 30
    SERIES = (
        ("New user accounts", "accounts", UserAccount.created_at),
        ("Designer applications received", "applications", DesignerApplication.submitted_at),
        ("Projects reported", "reports", Report.created_at),
        ("Reports resolved", "resolved", Report.resolved_at),
    )

    def activity(self, days=None):
        days = days if days in self.PERIODS else self.DEFAULT_DAYS
        timeline = ActivityTimeline.last_days(days)
        before = ActivityTimeline(timeline.start - timedelta(days=days), timeline.start, "day")
        series = []
        for title, unit, column in self.SERIES:
            counts = timeline.count(column)
            total = sum(v for v in counts if v is not None)
            previous = sum(v for v in before.count(column) if v is not None)
            series.append({"title": title, "unit": unit, "counts": counts, "total": total,
                           "previous": previous, "change": change(total, previous),
                           "change_text": change_text(change(total, previous))})
        return {
            "days": days,
            "labels": timeline.labels,
            "series": series,
        }
