from app.entity.db import db


class IDPPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    idp_id = db.Column(
        db.Integer,
        db.ForeignKey("idp.id"),
        nullable=False,
        index=True,
    )

    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(30), nullable=False)

    data = db.deferred(
        db.Column(db.LargeBinary, nullable=False)
    )

    @classmethod
    def get(cls, photo_id):
        return db.session.get(cls, photo_id)

    def delete(self):
        db.session.delete(self)
        db.session.commit()