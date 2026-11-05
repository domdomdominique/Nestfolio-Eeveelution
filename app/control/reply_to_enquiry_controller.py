from app.entity.enquiry import Enquiry
from app.entity.reply import Reply
from app.entity.user_account import UserAccount


class ReplyToEnquiryController:
    """Control: handles 'Reply to enquiry' (ID-21 AC3: the designer replies;
    the customer can then answer back on their My enquiries page).

    Only the enquiry's own designer or customer may reply, and their account
    must be active.
    """

    MAX_MESSAGE = Reply.MAX_MESSAGE

    def reply(self, sender_id, enquiry_id, message):
        enquiry = Enquiry.get(enquiry_id)
        sender = UserAccount.get(sender_id)
        if enquiry is None or sender is None or sender_id not in (enquiry.designer_id, enquiry.customer_id):
            raise LookupError("Enquiry not found.")  # never reveal other people's enquiries
        if sender.is_blocked:
            raise LookupError("Enquiry not found.")
        message = (message or "").strip()
        if not message:
            raise ValueError("Please write a reply before sending.")
        if len(message) > self.MAX_MESSAGE:
            raise ValueError(f"Please keep your reply under {self.MAX_MESSAGE} characters.")
        return Reply.add(enquiry, sender_id, message)
