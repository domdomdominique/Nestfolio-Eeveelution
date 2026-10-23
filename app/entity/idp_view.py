from datetime import datetime, timedelta

from app.entity.db import db


class IDPView(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    idp_id = db.Column(
        db.Integer,
        db.ForeignKey("idp.id"),
        nullable=False,
        index=True,
    )

    category = db.Column(db.String(50), nullable=False)

    viewed_at = db.Column(
        db.DateTime,
        default=datetime.now,
        nullable=False,
        index=True,
    )

    @classmethod
    def trends(cls, days):
        from app.entity.idp import IDP

        now = datetime.now()
        cutoff = now - timedelta(days=days)

        query = cls.query.join(
            IDP,
            cls.idp_id == IDP.id,
        )

        query = IDP.visible(query).filter(
            cls.viewed_at >= cutoff,
            cls.viewed_at <= now,
        )

        count = db.func.count(cls.id)

        categories = (
            query.with_entities(cls.category, count)
            .group_by(cls.category)
            .order_by(count.desc(), cls.category)
            .all()
        )

        projects = (
            query.with_entities(IDP, count)
            .group_by(IDP.id)
            .order_by(count.desc(), IDP.id)
            .limit(10)
            .all()
        )

        return categories, projects