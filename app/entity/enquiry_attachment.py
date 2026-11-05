from app.entity.db import db


class EnquiryAttachment(db.Model):
    """Entity: a photo (JPG/PNG) or PDF sent in an enquiry conversation (C-16, ID-21).

    reply_id is empty for files sent with the customer's first message, and set for
    files sent with a later reply by either the customer or the designer. Only the
    enquiry's customer and designer may open it; the file is kept in the database
    like IDP photos, and only loaded when it is downloaded.
    """

    id = db.Column(db.Integer, primary_key=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey("enquiry.id"), nullable=False, index=True)
    reply_id = db.Column(db.Integer, db.ForeignKey("reply.id"), index=True)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(30), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    data = db.deferred(db.Column(db.LargeBinary, nullable=False))

    enquiry = db.relationship(
        "Enquiry",
        backref=db.backref("all_attachments", order_by="EnquiryAttachment.id",
                           cascade="all, delete-orphan", lazy="select"),
    )
    reply = db.relationship(
        "Reply",
        backref=db.backref("attachments", order_by="EnquiryAttachment.id", lazy="select"),
    )

    @classmethod
    def ensure_schema(cls):
        """Databases made before replies could carry files lack reply_id: add it (no data is lost)."""
        columns = {c["name"] for c in db.inspect(db.engine).get_columns(cls.__tablename__)}
        if "reply_id" not in columns:
            with db.engine.begin() as connection:
                connection.exec_driver_sql(
                    f"ALTER TABLE {cls.__tablename__} ADD COLUMN reply_id INTEGER REFERENCES reply(id)")

    @classmethod
    def get(cls, attachment_id):
        return db.session.get(cls, attachment_id)

    @property
    def is_image(self):
        return self.content_type.startswith("image/")

    @property
    def size_label(self):
        if self.size >= 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        return f"{max(1, round(self.size / 1024))} KB"
