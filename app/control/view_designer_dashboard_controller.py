from datetime import datetime

from app.entity.announcement import Announcement
from app.entity.enquiry import Enquiry
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


class ViewDesignerDashboardController:
    """Control: gathers what the designer's dashboard shows (ID-01 landing page, ID-13, ID-14)."""

    def view(self, designer_id):
        account = UserAccount.get(designer_id)
        if account is None:
            raise LookupError("Account not found.")
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        totals = IDP.totals_for_designer(designer_id)
        return {
            "account": account,
            "announcements": Announcement.latest(3, role="designer", user_id=designer_id),
            "company": account.company,
            "project_count": IDP.count_for_designer(designer_id),
            "added_this_month": IDP.added_since(designer_id, month_start),
            "views": totals["views"],
            "shortlists": totals["shortlists"],
            "enquiry_count": Enquiry.count_for_designer(designer_id),
            "projects": IDP.top_for_designer(designer_id, 5),
            "recent_enquiries": Enquiry.for_designer(designer_id, limit=3),
        }
