from app.entity.enquiry_attachment import EnquiryAttachment
from app.entity.user_account import UserAccount


class ViewEnquiryAttachmentController:
    """Control: open a photo or PDF attached to an enquiry (C-16, ID-21).

    Only the enquiry's customer and designer may open it, and their account must be
    active; anyone else is told it does not exist.
    """

    def view(self, user_id, attachment_id):
        attachment = EnquiryAttachment.get(attachment_id)
        viewer = UserAccount.get(user_id)
        if (attachment is None or viewer is None or viewer.is_blocked
                or user_id not in (attachment.enquiry.designer_id, attachment.enquiry.customer_id)):
            raise LookupError("Attachment not found.")
        return attachment
