from datetime import datetime

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import selectinload

from app.entity.db import db
from app.entity.encryption import EncryptedString


class Enquiry(db.Model):
    """Entity: a message a customer sends to an interior designer."""

    id = db.Column(db.Integer, primary_key=True)
    designer_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    idp_id = db.Column(db.Integer, db.ForeignKey("idp.id"))  # set when sent from a project page
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(EncryptedString, nullable=False)  # email or phone to reply to, encrypted in the database
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    idp = db.relationship("IDP")

    # C-16 Save a customer's message to a designer, with any photos or PDFs attached,
    # in one step; the contact is stored encrypted.
    @classmethod
    def send(cls, designer_id, customer_id, name, contact, message, idp_id=None, attachments=()):
        from app.entity.enquiry_attachment import EnquiryAttachment

        enquiry = cls(designer_id=designer_id, customer_id=customer_id, idp_id=idp_id,
                      name=name, contact=contact, message=message)
        enquiry.all_attachments = [EnquiryAttachment(**a) for a in attachments]
        db.session.add(enquiry)
        db.session.commit()
        return enquiry

    @classmethod
    def _with_conversation(cls):
        """A query that also reads each enquiry's replies, files and project in bulk. The inbox and the
        unread badge (which runs on every page) show all of them, so this avoids one query per enquiry.
        The file bytes stay deferred; only their names and sizes are read."""
        from app.entity.enquiry_attachment import EnquiryAttachment  # noqa: F401  (defines all_attachments)
        from app.entity.reply import Reply

        return cls.query.options(selectinload(cls.replies).selectinload(Reply.attachments),
                                 selectinload(cls.all_attachments), selectinload(cls.idp))

    @classmethod
    def for_designer(cls, designer_id, limit=None):
        """ID-21 Return this designer's enquiries, newest first."""
        query = (
            cls._with_conversation().filter_by(designer_id=designer_id)
            .order_by(
                cls.created_at.desc(),
                cls.id.desc(),
            )
        )

        if limit is not None:
            query = query.limit(limit)

        return query.all()


    @classmethod
    def count_for_designer(cls, designer_id):
        return cls.query.filter_by(designer_id=designer_id).count()

    # --- Replies (ID-21 AC3 and AC5) -------------------------------------------------------

    @classmethod
    def get(cls, enquiry_id):
        return db.session.get(cls, enquiry_id)

    @classmethod
    def for_customer(cls, customer_id):
        """The enquiries a customer has sent, newest first, for their My enquiries page."""
        return (cls._with_conversation().filter_by(customer_id=customer_id)
                .order_by(cls.created_at.desc(), cls.id.desc()).all())

    @classmethod
    def latest_between(cls, customer_id, designer_id, idp_id=None, any_project=False):
        """The newest conversation this customer has with this designer: about the given
        project, or about any project when any_project is True."""
        query = cls.query.filter_by(customer_id=customer_id, designer_id=designer_id)
        if not any_project:
            query = query.filter_by(idp_id=idp_id)
        return query.order_by(cls.created_at.desc(), cls.id.desc()).first()

    @property
    def designer(self):
        from app.entity.user_account import UserAccount

        return UserAccount.get(self.designer_id)

    def new_messages_for(self, user_id, seen_at):
        """Messages from the other person this user has not seen yet (for notifications).
        For the designer the customer's original message counts too."""
        new = 0
        if user_id == self.designer_id and (seen_at is None or self.created_at > seen_at):
            new += 1
        new += sum(1 for r in self.replies if r.sender_id != user_id and (seen_at is None or r.created_at > seen_at))
        return new

    @classmethod
    def unread_count_for(cls, user_id):
        """How many of this person's conversations have something new (the badge). Same rule as
        new_messages_for, but counted in the database: it runs on every page, so it must not load them all."""
        from app.entity.reply import EnquirySeen, Reply

        newer = or_(EnquirySeen.seen_at.is_(None), Reply.created_at > EnquirySeen.seen_at)
        new_reply = exists().where(and_(Reply.enquiry_id == cls.id, Reply.sender_id != user_id, newer))
        new_enquiry = and_(cls.designer_id == user_id,
                           or_(EnquirySeen.seen_at.is_(None), cls.created_at > EnquirySeen.seen_at))
        return (db.session.query(func.count(cls.id))
                .outerjoin(EnquirySeen, and_(EnquirySeen.enquiry_id == cls.id, EnquirySeen.user_id == user_id))
                .filter(or_(cls.designer_id == user_id, cls.customer_id == user_id))
                .filter(or_(new_enquiry, new_reply))
                .scalar())

    @property
    def last_message_from_designer(self):
        """True once the designer has answered the customer's latest message."""
        return bool(self.replies) and self.replies[-1].sender_id == self.designer_id

    @property
    def conversation(self):
        """The whole conversation in order: the customer's first message, then every reply."""
        first = Message(self.customer_id, self.message, self.created_at, self.attachments)
        return [first] + [Message(r.sender_id, r.message, r.created_at, r.attachments) for r in self.replies]

    @property
    def attachments(self):
        """The files sent with the customer's first message (replies carry their own)."""
        return [a for a in self.all_attachments if a.reply_id is None]

    @property
    def last_activity(self):
        return self.replies[-1].created_at if self.replies else self.created_at

    def mentions(self, text):
        """True if the search text appears in the name, project title or any message."""
        text = text.lower()
        words = [self.name, self.idp.title if self.idp else "", self.designer.display_name if self.designer else ""]
        words += [m.message for m in self.conversation]
        return any(text in (w or "").lower() for w in words)


class Message:
    """One speech bubble in an enquiry conversation (not stored: built from Enquiry and Reply)."""

    def __init__(self, sender_id, message, created_at, attachments=()):
        self.sender_id = sender_id
        self.message = message
        self.created_at = created_at
        self.attachments = list(attachments)  # photos/PDFs sent with this message
