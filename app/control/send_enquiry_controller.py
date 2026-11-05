from app.control.enquiry_attachment_validation import validated_attachments
from app.control.signup_validation import clean_email, clean_phone
from app.entity.enquiry import Enquiry
from app.entity.idp import IDP
from app.entity.user_account import UserAccount


class SendEnquiryController:
    """Control: handles the Customer 'Contact ID' use case (C-16)."""

    MAX_MESSAGE = 2000

    def start(self, customer_id, designer_id, idp_id=None):
        """Open the 'new enquiry' pane from a project or designer page (C-16 AC1).

        Returns (designer, project, existing): when the customer has already written to
        this designer about this project (or, from the designer page, about anything),
        existing is that conversation so the page can open it instead of a duplicate."""
        designer = UserAccount.get(designer_id)
        if designer is None or designer.role != "designer" or designer.is_suspended:
            raise LookupError("Designer not found.")
        idp = IDP.get(idp_id) if idp_id else None
        if idp is not None and (idp.designer_id != designer.id or not idp.is_visible):
            idp = None
        existing = Enquiry.latest_between(customer_id, designer.id, idp.id if idp else None,
                                          any_project=idp_id is None)
        return designer, idp, existing

    def latest(self, customer_id, designer_id):
        """The conversation the customer has just started, so the page can open it."""
        return Enquiry.latest_between(customer_id, designer_id, any_project=True)

    def send(self, customer_id, designer_id, name, contact, message, idp_id=None, files=()):
        """files are the uploaded photos (JPG/PNG) and PDFs to attach, checked before anything is saved."""
        designer = UserAccount.get(designer_id)
        if designer is None or designer.role != "designer" or designer.is_suspended:
            raise LookupError("Designer not found.")
        name, contact, message = ((v or "").strip() for v in (name, contact, message))
        if not name:
            raise ValueError("Please enter your name.")
        if not contact:
            raise ValueError("Please enter an email or phone number the designer can reply to.")
        try:
            contact = clean_email(contact) if "@" in contact else clean_phone(contact)
        except ValueError:
            raise ValueError("Please enter a valid email address or 8-digit Singapore phone number.") from None
        if not message:
            raise ValueError("Please write a message for the designer.")
        if len(message) > self.MAX_MESSAGE:
            raise ValueError(f"Please keep your message under {self.MAX_MESSAGE} characters.")
        attachments = validated_attachments(files)
        # Only link the project if it really belongs to this designer
        idp = IDP.get(idp_id) if idp_id else None
        idp_id = idp.id if idp and idp.designer_id == designer.id else None
        Enquiry.send(designer.id, customer_id, name, contact, message, idp_id, attachments)
        return designer
