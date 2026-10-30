from datetime import date

from app.entity.activity_report import ActivityReport


class GenerateReportController:
    """Control: handles the Platform Management 'Generate daily / weekly / monthly
    report' use cases (PM-08, PM-09, PM-10).

    Dates come from the page as text: 'YYYY-MM-DD' for a day or week
    (any day in the week), 'YYYY-MM' for a month.
    """

    KINDS = ("daily", "weekly", "monthly")

    def generate(self, kind, value):
        if kind not in self.KINDS:
            raise ValueError("Please choose a daily, weekly or monthly report.")
        try:
            if kind == "monthly":
                year, month = self._parse_month(value)
                return ActivityReport.monthly(year, month)
            day = self._parse_day(value)
            return ActivityReport.daily(day) if kind == "daily" else ActivityReport.weekly(day)
        except OverflowError:  # a range that runs past year 9999
            raise ValueError("Please choose a valid date.") from None

    def daily(self, day):
        return ActivityReport.daily(day)

    def weekly(self, any_day):
        return ActivityReport.weekly(any_day)

    def monthly(self, year, month):
        return ActivityReport.monthly(year, month)

    @staticmethod
    def _parse_day(value):
        try:
            return date.fromisoformat((value or "").strip())
        except ValueError:
            raise ValueError("Please choose a valid date.") from None

    @staticmethod
    def _parse_month(value):
        try:
            year, month = (int(part) for part in (value or "").strip().split("-"))
            date(year, month, 1)
        except ValueError:
            raise ValueError("Please choose a valid month.") from None
        return year, month
