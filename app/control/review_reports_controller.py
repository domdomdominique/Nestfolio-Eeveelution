from app.entity.announcement import Announcement
from app.entity.report import Report


class ReviewReportsController:
    """Control: handles the User Admin 'Review reported IDPs' use case (UA-17).

    Customers create reports through ReportIDPController (C-15); this is
    where they show up for the User Admin to review.
    """

    REASON_MAX = Report.REMOVAL_REASON_MAX

    def list_reports(self, status="open"):
        if status not in Report.STATUSES:
            status = "open"
        return Report.list_by_status(status)

    def open_count(self):
        return Report.count_open()

    def resolve(self, report_id, admin_id):
        """Same as dismiss(): kept so the existing 'Mark resolved' button still works."""
        return self.dismiss(report_id, admin_id)

    def dismiss(self, report_id, admin_id):
        """Close the report; the IDP stays visible to customers."""
        report = self._get(report_id)
        report.resolve(admin_id, "dismissed")
        return report

    def remove_idp(self, report_id, admin_id, reason=""):
        """Hide the reported IDP from customers and close every open report on it."""
        reason = (reason or "").replace("\r\n", "\n").strip()  # browsers count a line break as 1 character
        if not reason:
            raise ValueError("Please give a reason for removing this project.")
        if len(reason) > self.REASON_MAX:
            raise ValueError(f"The reason must be {self.REASON_MAX} characters or fewer.")
        report = self._get(report_id)
        if report.status != "open":
            raise ValueError("This report has already been resolved.")
        idp = report.idp
        idp.remove()
        open_reports = Report.query.filter_by(idp_id=report.idp_id, status="open").all()
        for other in open_reports:
            other.resolve(admin_id, "removed", reason)
        self._notify_designer(idp, admin_id, reason, open_reports)
        return report

    @staticmethod
    def _notify_designer(idp, admin_id, reason, reports):
        """Tell the designer, through a personal announcement, that their IDP was reported and removed."""
        reported_for = ", ".join(dict.fromkeys(r.reason for r in reports)) or "Not given"
        title = f"Project removed: {idp.title}"[:150]
        message = (
            f"Your project “{idp.title}” was reported by customers and has been removed "
            "from public view by a User Admin.\n\n"
            f"Reported for: {reported_for}\n"
            f"Reason for removal: {reason}"
        )
        Announcement.send(admin_id, title, message, recipient_id=idp.designer_id)

    @staticmethod
    def _get(report_id):
        report = Report.get(report_id)
        if report is None:
            raise ValueError("Report not found.")
        return report
