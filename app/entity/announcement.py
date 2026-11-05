from datetime import datetime

from app.entity.db import db


class Announcement(db.Model):
    """Entity: a message from a User Admin to every user, or only to chosen roles (UA-18).

    An announcement with no AnnouncementRole rows goes to everyone; otherwise only
    accounts whose role (UserProfile key) is listed see it.
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.now)

    admin = db.relationship("UserAccount")
    audience = db.relationship("AnnouncementRole", cascade="all, delete-orphan",
                               order_by="AnnouncementRole.id", lazy="selectin")

    @classmethod
    def send(cls, admin_id, title, message, roles=()):
        announcement = cls(admin_id=admin_id, title=title, message=message,
                           audience=[AnnouncementRole(role=role) for role in roles])
        db.session.add(announcement)
        db.session.commit()
        return announcement

    @classmethod
    def delete_by_id(cls, announcement_id):
        announcement = db.session.get(cls, announcement_id)
        if announcement is None:
            return False
        db.session.delete(announcement)
        db.session.commit()
        return True

    @classmethod
    def latest(cls, limit=None, role=None):
        """Newest first. With a role, only the announcements that role should see."""
        query = cls.query
        if role is not None:
            targeted = db.session.query(AnnouncementRole.announcement_id)
            query = query.filter(db.or_(
                ~cls.id.in_(targeted),  # sent to everyone
                cls.id.in_(targeted.filter(AnnouncementRole.role == role)),
            ))
        query = query.order_by(cls.sent_at.desc(), cls.id.desc())
        return (query.limit(limit) if limit else query).all()

    @property
    def role_keys(self):
        """The roles this was sent to; empty means everyone."""
        return [a.role for a in self.audience]

    @property
    def is_for_everyone(self):
        return not self.audience


class AnnouncementRole(db.Model):
    """Entity: one role (UserProfile key) an announcement was pushed to (UA-18)."""

    __table_args__ = (db.UniqueConstraint("announcement_id", "role"),)

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcement.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
