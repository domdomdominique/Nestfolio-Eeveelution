from datetime import datetime

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

    @classmethod
    def send(cls, designer_id, customer_id, name, contact, message, idp_id=None):
        enquiry = cls(designer_id=designer_id, customer_id=customer_id, idp_id=idp_id,
                      name=name, contact=contact, message=message)
        db.session.add(enquiry)
        db.session.commit()
        return enquiry

    @classmethod
    def for_designer(cls, designer_id, limit=None):
        """Return this designer's enquiries, newest first."""
        query = (
            cls.query.filter_by(designer_id=designer_id)
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
