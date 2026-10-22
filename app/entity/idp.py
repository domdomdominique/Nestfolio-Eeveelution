from datetime import datetime

from app.entity.db import db


class IDP(db.Model):
    """Entity: an Interior Design Project in a designer's portfolio."""

    CATEGORIES = ("Living Room", "Kitchen", "Bedroom", "Bathroom", "Study & Office", "Whole Home")

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(50), nullable=False)
    designer_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    view_count = db.Column(db.Integer, default=0)
    shortlist_count = db.Column(db.Integer, default=0)
    is_current = db.Column(db.Boolean, default=False)  # current (in progress) vs past project
    created_at = db.Column(db.DateTime, default=datetime.now)

    designer = db.relationship("UserAccount")

    @classmethod
    def categories(cls):
        """The categories a designer may pick (ID-12). One place to swap in a Category table later."""
        return cls.CATEGORIES

    @classmethod
    def get(cls, idp_id):
        return db.session.get(cls, idp_id)

    @classmethod
    def visible(cls, query=None):
        """Only IDPs whose designer is active (not suspended) — what customers may see (C-04)."""
        from app.entity.user_account import UserAccount

        query = cls.query if query is None else query
        return (query.join(UserAccount, cls.designer_id == UserAccount.id)
                .filter(UserAccount.is_suspended.isnot(True)))

    @property
    def is_visible(self):
        return not (self.designer and self.designer.is_suspended)

    @classmethod
    def search(cls, keyword):
        """Case-insensitive search on title or category."""
        if not keyword:
            return cls.query.order_by(cls.id).all()
        pattern = f"%{keyword}%"
        return (
            cls.query.filter(db.or_(cls.title.ilike(pattern), cls.category.ilike(pattern)))
            .order_by(cls.id)
            .all()
        )

    @classmethod
    def browse(cls, keyword="", categories=(), status=None, sort="views"):
        """Search, filter and sort projects for the Browse Projects page.

        keyword matches title, description, category or the designer's
        company/personal name; categories is a list of category names
        (empty = all); status is None, 'current' or 'past'; sort is 'views'
        (most viewed) or 'newest'. Suspended designers' IDPs are never returned.
        """
        from app.entity.designer_application import DesignerApplication
        from app.entity.user_account import UserAccount

        query = cls.visible()
        if keyword:
            pattern = f"%{keyword}%"
            query = (
                query.outerjoin(DesignerApplication, DesignerApplication.account_id == UserAccount.id)
                .filter(db.or_(cls.title.ilike(pattern), cls.description.ilike(pattern),
                               cls.category.ilike(pattern),
                               UserAccount.name.ilike(pattern),
                               DesignerApplication.company_name.ilike(pattern)))
            )
        if categories:
            query = query.filter(cls.category.in_(categories))
        if status in ("current", "past"):
            query = query.filter(cls.is_current == (status == "current"))
        order = cls.created_at.desc() if sort == "newest" else cls.view_count.desc()
        return query.order_by(order, cls.id.desc()).all()

    @classmethod
    def count_by_status(cls):
        current = cls.visible().filter(cls.is_current.is_(True)).count()
        return {"current": current, "past": cls.visible().count() - current}

    @classmethod
    def more_by_designer(cls, designer_id, exclude_id, limit=4):
        """The designer's other projects, most viewed first."""
        return (
            cls.visible().filter(cls.designer_id == designer_id, cls.id != exclude_id)
            .order_by(cls.view_count.desc(), cls.id.desc())
            .limit(limit)
            .all()
        )

    def record_view(self):
        self.view_count = (self.view_count or 0) + 1
        db.session.commit()

    @classmethod
    def popular(cls, sort="views", limit=4):
        """Most viewed (default) or newest projects."""
        order = cls.created_at.desc() if sort == "newest" else cls.view_count.desc()
        return cls.visible().order_by(order, cls.id.desc()).limit(limit).all()

    @classmethod
    def count_by_category(cls):
        rows = cls.visible(db.session.query(cls.category, db.func.count(cls.id))).group_by(cls.category)
        return dict(rows.all())

    @classmethod
    def top_designer_ids(cls, limit=3):
        """IDs of the (active) designers with the most projects."""
        rows = (
            cls.visible(db.session.query(cls.designer_id))
            .group_by(cls.designer_id)
            .order_by(db.func.count(cls.id).desc(), cls.designer_id)
            .limit(limit)
        )
        return [designer_id for (designer_id,) in rows]

    @classmethod
    def by_designer(cls, designer_id, status=None):
        """A designer's projects; status is None (all), 'current' or 'past'."""
        query = cls.query.filter_by(designer_id=designer_id)
        if status in ("current", "past"):
            query = query.filter_by(is_current=(status == "current"))
        return query.order_by(cls.is_current.desc(), cls.view_count.desc()).all()

    @classmethod
    def count_for_designer(cls, designer_id):
        return cls.query.filter_by(designer_id=designer_id).count()

    # --- Designer portfolio (ID-06 to ID-11) -----------------------------------
    # Every query below is scoped to the owning designer, so one designer can
    # never read or change another designer's project.

    @classmethod
    def get_owned(cls, idp_id, designer_id):
        """The designer's own IDP, or None (also None when it belongs to someone else)."""
        return cls.query.filter_by(id=idp_id, designer_id=designer_id).first()

    @classmethod
    def create(cls, designer_id, title, description, category, is_current):
        idp = cls(designer_id=designer_id, title=title, description=description,
                  category=category, is_current=is_current)
        db.session.add(idp)
        db.session.commit()
        return idp

    def update(self, title, description, category, is_current):
        self.title, self.description = title, description
        self.category, self.is_current = category, is_current
        db.session.commit()

    def set_current(self, is_current):
        self.is_current = is_current
        db.session.commit()

    def delete(self):
        """Remove the IDP, the favourites and reports that point at it, and unlink enquiries."""
        from app.entity.enquiry import Enquiry
        from app.entity.favourite import Favourite
        from app.entity.report import Report

        Favourite.query.filter_by(idp_id=self.id).delete()
        Report.query.filter_by(idp_id=self.id).delete()
        Enquiry.query.filter_by(idp_id=self.id).update({"idp_id": None})
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def _portfolio_query(cls, designer_id, keyword="", status=None, category=None):
        query = cls.query.filter_by(designer_id=designer_id)
        if keyword:
            escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(cls.title.ilike(f"%{escaped}%", escape="\\"))
        if status in ("current", "past"):
            query = query.filter(cls.is_current == (status == "current"))
        if category:
            query = query.filter(cls.category == category)
        return query

    @classmethod
    def portfolio(cls, designer_id, keyword="", status=None, category=None, limit=None, offset=0):
        """A designer's own projects, newest first, filtered by title keyword, status and category."""
        query = (cls._portfolio_query(designer_id, keyword, status, category)
                 .order_by(cls.created_at.desc(), cls.id.desc()).offset(offset))
        return (query.limit(limit) if limit else query).all()

    @classmethod
    def portfolio_count(cls, designer_id, keyword="", status=None, category=None):
        return cls._portfolio_query(designer_id, keyword, status, category).count()

    @classmethod
    def top_for_designer(cls, designer_id, limit=5):
        """A designer's most viewed projects."""
        return (cls.query.filter_by(designer_id=designer_id)
                .order_by(cls.view_count.desc(), cls.id.desc()).limit(limit).all())

    @classmethod
    def added_since(cls, designer_id, since):
        return cls.query.filter(cls.designer_id == designer_id, cls.created_at >= since).count()

    @classmethod
    def status_counts_for_designer(cls, designer_id):
        total = cls.count_for_designer(designer_id)
        current = cls.query.filter_by(designer_id=designer_id, is_current=True).count()
        return {"all": total, "current": current, "past": total - current}

    @classmethod
    def totals_for_designer(cls, designer_id):
        """Summed views and shortlists across a designer's projects (ID-13, ID-14)."""
        views, shortlists = db.session.query(
            db.func.coalesce(db.func.sum(cls.view_count), 0),
            db.func.coalesce(db.func.sum(cls.shortlist_count), 0),
        ).filter(cls.designer_id == designer_id).one()
        return {"views": int(views), "shortlists": int(shortlists)}
