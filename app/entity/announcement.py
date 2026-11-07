from datetime import datetime

from app.entity.db import db


class Announcement(db.Model):
    """Entity: a message from a User Admin to every user, or only to chosen roles (UA-18).

    An announcement with no AnnouncementRole rows goes to everyone; otherwise only
    accounts whose role (UserProfile key) is listed see it. An announcement with a
    recipient_id is a personal notice that only that one account sees (for example,
    telling a designer that a reported IDP was removed, UA-17).
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.now)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), index=True)

    admin = db.relationship("UserAccount", foreign_keys=[admin_id])
    recipient = db.relationship("UserAccount", foreign_keys=[recipient_id])
    audience = db.relationship("AnnouncementRole", cascade="all, delete-orphan",
                               order_by="AnnouncementRole.id", lazy="selectin")

    @classmethod
    def ensure_schema(cls):
        """Databases made before personal notices lack recipient_id: add it (no data is lost)."""
        columns = {c["name"] for c in db.inspect(db.engine).get_columns(cls.__tablename__)}
        if "recipient_id" not in columns:
            with db.engine.begin() as connection:
                connection.exec_driver_sql(
                    f"ALTER TABLE {cls.__tablename__} ADD COLUMN recipient_id INTEGER REFERENCES user_account(id)")

    @classmethod
    def send(cls, admin_id, title, message, roles=(), recipient_id=None):
        announcement = cls(admin_id=admin_id, title=title, message=message,
                           recipient_id=recipient_id,
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
    def latest(cls, limit=None, role=None, user_id=None):
        """Newest first. With a role, only the announcements that role should see, plus the
        personal notices sent to user_id."""
        query = cls.query
        if role is not None:
            targeted = db.session.query(AnnouncementRole.announcement_id)
            for_role = db.and_(cls.recipient_id.is_(None), db.or_(
                ~cls.id.in_(targeted),  # sent to everyone
                cls.id.in_(targeted.filter(AnnouncementRole.role == role)),
            ))
            query = query.filter(
                db.or_(for_role, cls.recipient_id == user_id) if user_id is not None else for_role)
        query = query.order_by(cls.sent_at.desc(), cls.id.desc())
        return (query.limit(limit) if limit else query).all()

    @property
    def role_keys(self):
        """The roles this was sent to; empty means everyone."""
        return [a.role for a in self.audience]

    @property
    def is_personal(self):
        return self.recipient_id is not None

    @property
    def is_for_everyone(self):
        return not self.audience and not self.is_personal


class AnnouncementRole(db.Model):
    """Entity: one role (UserProfile key) an announcement was pushed to (UA-18)."""

    __table_args__ = (db.UniqueConstraint("announcement_id", "role"),)

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcement.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
