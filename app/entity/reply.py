from datetime import datetime

from app.entity.db import db


class Reply(db.Model):
    """Entity: one message in an enquiry's conversation (ID-21 AC3 and AC5).

    The designer replies to a customer's enquiry, and the customer can answer
    back. Only the enquiry's designer and its customer may read or post.
    """

    MAX_MESSAGE = 2000

    id = db.Column(db.Integer, primary_key=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiry.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    enquiry = db.relationship(
        "Enquiry",
        backref=db.backref("replies", order_by="(Reply.created_at, Reply.id)",
                           cascade="all, delete-orphan", lazy="select"),
    )
    sender = db.relationship("UserAccount")

    @classmethod
    def add(cls, enquiry, sender_id, message, attachments=()):
        """Save a reply and any photos/PDFs sent with it, in one step.
        The controller has already checked the text and files; this checks access."""
        from app.entity.enquiry_attachment import EnquiryAttachment

        if sender_id not in (enquiry.designer_id, enquiry.customer_id):
            raise PermissionError("Only the designer and the customer can reply to this enquiry.")
        reply = cls(enquiry_id=enquiry.id, sender_id=sender_id, message=message)
        reply.attachments = [EnquiryAttachment(enquiry_id=enquiry.id, **a) for a in attachments]
        db.session.add(reply)
        db.session.commit()
        return reply

    @property
    def from_designer(self):
        return self.sender_id == self.enquiry.designer_id


class EnquirySeen(db.Model):
    """Entity: when a person last opened an enquiry conversation. Messages from the
    other person after that time count as new, for the notification badges."""

    __table_args__ = (db.UniqueConstraint("enquiry_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiry.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False, index=True)
    seen_at = db.Column(db.DateTime, nullable=False)

    @classmethod
    def last_seen(cls, enquiry_ids, user_id):
        """{enquiry_id: seen_at} for this person."""
        if not enquiry_ids:
            return {}
        rows = cls.query.filter(cls.enquiry_id.in_(enquiry_ids), cls.user_id == user_id).all()
        return {r.enquiry_id: r.seen_at for r in rows}

    @classmethod
    def mark(cls, enquiry_ids, user_id):
        """Record that this person has now seen these conversations."""
        now = datetime.now()
        seen = {r.enquiry_id: r for r in cls.query.filter(cls.enquiry_id.in_(enquiry_ids),
                                                         cls.user_id == user_id)} if enquiry_ids else {}
        for enquiry_id in enquiry_ids:
            if enquiry_id in seen:
                seen[enquiry_id].seen_at = now
            else:
                db.session.add(cls(enquiry_id=enquiry_id, user_id=user_id, seen_at=now))
        db.session.commit()
