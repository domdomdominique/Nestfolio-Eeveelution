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
        report.idp.remove()
        for other in Report.query.filter_by(idp_id=report.idp_id, status="open").all():
            other.resolve(admin_id, "removed", reason)
        return report

    @staticmethod
    def _get(report_id):
        report = Report.get(report_id)
        if report is None:
            raise ValueError("Report not found.")
        return report
