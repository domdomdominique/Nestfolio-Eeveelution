from app.entity.report import Report


class ReviewReportsController:
    """Control: handles the User Admin 'Review reported IDPs' use case (UA-17).

    Customers create reports through ReportIDPController (C-15); this is
    where they show up for the User Admin to review.
    """

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

    def remove_idp(self, report_id, admin_id):
        """Hide the reported IDP from customers and close every open report on it."""
        report = self._get(report_id)
        if report.status != "open":
            raise ValueError("This report has already been resolved.")
        report.idp.remove()
        for other in Report.query.filter_by(idp_id=report.idp_id, status="open").all():
            other.resolve(admin_id, "removed")
        return report

    @staticmethod
    def _get(report_id):
        report = Report.get(report_id)
        if report is None:
            raise ValueError("Report not found.")
        return report
