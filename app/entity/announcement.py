from datetime import datetime

from app.entity.db import db


class Announcement(db.Model):
    """Entity: a system-wide message from a User Admin to all users (UA-18)."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.now)

    admin = db.relationship("UserAccount")

    @classmethod
    def send(cls, admin_id, title, message):
        announcement = cls(admin_id=admin_id, title=title, message=message)
        db.session.add(announcement)
        db.session.commit()
        return announcement

    @classmethod
    def latest(cls, limit=None):
        query = cls.query.order_by(cls.sent_at.desc(), cls.id.desc())
        return (query.limit(limit) if limit else query).all()
