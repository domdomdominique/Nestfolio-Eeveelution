from app.control.enquiry_attachment_validation import validated_attachments
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

    def reply(self, sender_id, enquiry_id, message, files=()):
        """files are photos (JPG/PNG) or PDFs to send with the reply; a reply may be files only."""
        enquiry = Enquiry.get(enquiry_id)
        sender = UserAccount.get(sender_id)
        if enquiry is None or sender is None or sender_id not in (enquiry.designer_id, enquiry.customer_id):
            raise LookupError("Enquiry not found.")  # never reveal other people's enquiries
        if sender.is_blocked:
            raise LookupError("Enquiry not found.")
        message = (message or "").strip()
        if len(message) > self.MAX_MESSAGE:
            raise ValueError(f"Please keep your reply under {self.MAX_MESSAGE} characters.")
        attachments = validated_attachments(files)
        if not message and not attachments:
            raise ValueError("Please write a reply or attach a file before sending.")
        return Reply.add(enquiry, sender_id, message, attachments)
