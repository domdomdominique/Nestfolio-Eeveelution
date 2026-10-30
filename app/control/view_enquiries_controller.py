from app.entity.enquiry import Enquiry
from app.entity.user_account import UserAccount


# ID-21 Designer's enquiry list, newest first (replies are not built yet).
class ViewEnquiriesController:
    def _check_designer(self, designer_id):
        account = UserAccount.get(designer_id)

        if (
            account is None
            or account.role != "designer"
            or account.is_suspended
        ):
            raise LookupError("Designer account not found.")

    def view(self, designer_id):
        self._check_designer(designer_id)
        return Enquiry.for_designer(designer_id)

    def count(self, designer_id):
        self._check_designer(designer_id)
        return Enquiry.count_for_designer(designer_id)