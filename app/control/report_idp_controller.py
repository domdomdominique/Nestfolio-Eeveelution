from app.entity.idp import IDP
from app.entity.report import Report


class ReportIDPController:
    """Control: handles the Customer 'Report IDP' use case (C-15)."""

    MAX_DETAILS = 1000

    def reasons(self):
        return Report.REASONS

    def report(self, customer_id, idp_id, reason, details=""):
        idp = IDP.get(idp_id)
        if idp is None or not idp.is_visible:
            raise LookupError("Project not found.")
        if Report.exists(customer_id, idp_id):
            raise ValueError("You have already reported this project. Our admin team will review it.")
        if reason not in Report.REASONS:
            raise ValueError("Please choose a reason for your report.")
        details = (details or "").strip()
        if len(details) > self.MAX_DETAILS:
            raise ValueError(f"Please keep the details under {self.MAX_DETAILS} characters.")
        return Report.submit(customer_id, idp_id, reason, details)
