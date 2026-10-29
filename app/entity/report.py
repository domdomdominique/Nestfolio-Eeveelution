from datetime import datetime

from app.entity.db import db


class Report(db.Model):
    """Entity: a customer's report that an IDP is inappropriate (reviewed by a User Admin)."""

    REASONS = (
        "Spam or advertising",
        "Wrong or misleading information",
        "Inappropriate photos or content",
        "Copied from another designer",
        "Other",
    )

    id = db.Column(db.Integer, primary_key=True)
    idp_id = db.Column(db.Integer, db.ForeignKey("idp.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, default="")
    STATUSES = ("open", "resolved")

    status = db.Column(db.String(20), default="open", nullable=False)  # open / resolved
    created_at = db.Column(db.DateTime, default=datetime.now)
    resolved_at = db.Column(db.DateTime)
    resolution = db.Column(db.String(20))  # dismissed (IDP stays) / removed (IDP hidden) - UA-17
    resolved_by = db.Column(db.Integer, db.ForeignKey("user_account.id"))  # the User Admin

    idp = db.relationship("IDP")
    customer = db.relationship("UserAccount", foreign_keys=[customer_id])

    # A customer can report each IDP only once (C-15)
    __table_args__ = (db.UniqueConstraint("customer_id", "idp_id"),)

    @classmethod
    def exists(cls, customer_id, idp_id):
        return cls.query.filter_by(customer_id=customer_id, idp_id=idp_id).first() is not None

    @classmethod
    def submit(cls, customer_id, idp_id, reason, details=""):
        report = cls(customer_id=customer_id, idp_id=idp_id, reason=reason, details=details)
        db.session.add(report)
        db.session.commit()
        return report

    @classmethod
    def count_open(cls):
        return cls.query.filter_by(status="open").count()

    @classmethod
    def get(cls, report_id):
        return db.session.get(cls, report_id)

    @classmethod
    def list_by_status(cls, status):
        """Reports for the User Admin's review list (UA-17), newest first."""
        return cls.query.filter_by(status=status).order_by(cls.created_at.desc(), cls.id.desc()).all()

    def resolve(self, admin_id, resolution="dismissed"):
        if self.status != "open":
            raise ValueError("This report has already been resolved.")
        self.status = "resolved"
        self.resolution = resolution
        self.resolved_by = admin_id
        self.resolved_at = datetime.now()
        db.session.commit()
