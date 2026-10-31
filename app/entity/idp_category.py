from datetime import datetime

from app.entity.db import db


class IDPCategory(db.Model):
    """Entity: a category designers classify their IDPs under (PM-03 to PM-07).

    IDP.category stores the category *name*, so renaming a category also
    renames it on every IDP that uses it (PM-05).
    """

    # Created automatically on first run so the site works out of the box
    DEFAULTS = (
        ("Living Room", "Living and family rooms."),
        ("Kitchen", "Kitchens and dining areas."),
        ("Bedroom", "Master and common bedrooms."),
        ("Bathroom", "Bathrooms and toilets."),
        ("Study & Office", "Home offices and study rooms."),
        ("Whole Home", "Full-home renovations."),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    @classmethod
    def ensure_defaults(cls):
        if cls.query.count() == 0:
            db.session.add_all(cls(name=n, description=d) for n, d in cls.DEFAULTS)
            db.session.commit()

    @classmethod
    def get(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def name_exists(cls, name, exclude_id=None):
        query = cls.query.filter(db.func.lower(cls.name) == name.lower())
        if exclude_id is not None:
            query = query.filter(cls.id != exclude_id)
        return query.first() is not None

    @classmethod
    def create(cls, name, description=""):
        category = cls(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        return category

    @classmethod
    def list_all(cls, keyword=""):
        query = cls.query
        if keyword:
            query = query.filter(cls.name.icontains(keyword, autoescape=True))
        return query.order_by(cls.name).all()

    @classmethod
    def names(cls):
        """Category names in display order, for designer forms and customer filters."""
        return [c.name for c in cls.query.order_by(cls.id)]

    @property
    def idp_count(self):
        from app.entity.idp import IDP

        return IDP.query.filter_by(category=self.name).count()

    def update(self, name, description):
        from app.entity.idp import IDP

        if name != self.name:
            IDP.query.filter_by(category=self.name).update({"category": name})
        self.name, self.description = name, description
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
