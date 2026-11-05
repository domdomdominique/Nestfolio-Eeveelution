from app.entity.enquiry import Enquiry
from app.entity.user_account import UserAccount


class ViewMyEnquiriesController:
    """Control: the customer's 'My enquiries' page (ID-21 AC5: the customer sees
    the designer's replies). Lists the enquiries they sent, newest first."""

    def view(self, customer_id):
        account = UserAccount.get(customer_id)
        if account is None or account.role != "customer":
            raise LookupError("Customer account not found.")
        return Enquiry.for_customer(customer_id)

    def count_answered(self, customer_id):
        """How many of the customer's enquiries have a designer reply waiting for them."""
        return sum(1 for e in Enquiry.for_customer(customer_id) if e.last_message_from_designer)
