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
        report = Report.get(report_id)
        if report is None:
            raise ValueError("Report not found.")
        report.resolve(admin_id)
        return report
